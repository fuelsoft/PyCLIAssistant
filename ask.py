#! /bin/env python

# LLM-based command line assistant

import os
import re
import sys
import json
import shutil
import platform
import subprocess
from enum import Enum
from datetime import datetime

from PyLLMAdapter.Ollama import Ollama

REQ_CONFIRM = True
DEBUG = False

# If you are not running locally, change these values
# Codestral is the model I've tested against and what the prompts below are tuned for
ol = Ollama(model = "codestral", ip = "localhost", port = 11434)

def get_platform_data(default_shell = "bash"):
	kernel_to_platform = {
		"darwin": "macos"
	}

	p = platform.system().lower()
	s = default_shell

	if p in ['linux', 'darwin']:
		s = os.environ.get('SHELL', s).split('/')[-1]

	elif p == 'windows':
		s = os.environ.get('COMSPEC', s).split('\\')[-1].split('.')[0]

	if p in kernel_to_platform:
		p = kernel_to_platform[p]

	return [p, s]

pdata = get_platform_data()
PLATFORM = pdata[0]
SHELL = pdata[1]

sys_prompt = """
You are assisting a user sitting at a command line.
This shell is {shell} on {platform}.
The current date and time is {datetime}.
The user asks for assistance with the following: "{prompt}".
You must format your reply as JSON.
When replying, you may do one of two things:
	ask a clarifying question (put this under a key named "reply")
OR
	run a command required to perform the request (put this under a key named "run").

In any case, do not include any additional text - the reply must be valid JSON.
Avoid running commands that modify the system by changing settings or modifying files.
"""

sys_reply = """
STDOUT
```{shell}
{stdout}
```

STDERR
```{shell}
{stderr}
```

The original user request was "{prompt}".

If this solved the request, incorporate it in an answer (put this under a key named "reply").
If this did not solve the request, you may run another command (put this under a key named "run").
In any case, do not include any additional text - the reply must be valid JSON.
"""

sys_explain = """
Explain the following command(s):

```{shell}
{command}
```

Explain what all parameters and flags do, if any are specified.
If this could result in any side-effects, make note of them.
"""

# usage: ask.py <question>
def main():
	prompt = sys.argv[1]

	current_time = datetime.now()
	formatted_time = current_time.strftime("%Y/%m/%d %H:%M:%S")
	message = sys_prompt.format(shell = SHELL, platform = PLATFORM, datetime = formatted_time, prompt = prompt)

	reply = ol.chat(message, temperature = 0.3)
	output = handleReply(reply)

	while output is not None:
		stdout = output[0]
		stderr = output[1]

		# normally the temperature should be low - we don't want the model to get creative when summarizing the results
		# however, if there's error output, it may be better to set the temperature higher to encourage outside-the-box thinking on a workaround
		temperature = 0.3
		if len(stderr) > 0:
			temperature = 0.8

		message = sys_reply.format(shell = SHELL, stdout = stdout, stderr = stderr, prompt = prompt)
		if DEBUG: print(message)

		reply = ol.chat(message, temperature = temperature)
		output = handleReply(reply)

def handleReply(reply):
	action = json.loads(reply.message)

	if "run" in action:
		try:
			command = Command(action["run"])
		except Exception as e:
			print(f"Encountered exception when processing action: {action}")
			print(e)
			raise

		is_whitelisted, reason = command.is_whitelisted()
		user_input = "?"

		if REQ_CONFIRM:
			while user_input == "?":
				try:
					user_input = input(get_prompt(command, is_whitelisted)).lower()
				except KeyboardInterrupt as e:
					print(colourize("\nCommand not executed. Exiting.", Colour.RED))
					sys.exit(0)

				if user_input == "?":
					print(colourize("Explaining...", Colour.CYAN))
					reply = ol.ask(sys_explain.format(shell = SHELL, command = command))
					print(f"\n{reply.message}\n")

		if is_whitelisted or user_input == "f":
			if not is_whitelisted:
				print(colourize("Allowing bypass...", Colour.MAGENTA))
			else:
				print(colourize("Running command...", Colour.GREEN))

			result = command.run()
			if DEBUG:
				print(f"STDOUT\n{result[0].rstrip()}\n")
				print(f"STDERR\n{result[1].rstrip()}\n")
			return result

		else:
			print(colourize(reason, Colour.RED))
			return ["", reason]

	elif "reply" in action:
		print(f"\n{action['reply']}")
		return None

	else:
		print(colourize(f"Unknown/malformed reply: {action}", Colour.RED))
		return None

def get_prompt(command, is_whitelisted):
	if is_whitelisted:
		options = {
			"Enter": colourize('run', Colour.GREEN),
			"?": colourize('explain', Colour.CYAN),
			"^C": colourize('abort', Colour.RED)
		}
	else:
		options = {
			"Enter": colourize('retry', Colour.GREEN),
			"F": colourize('bypass safety', Colour.MAGENTA),
			"?": colourize('explain', Colour.CYAN),
			"^C": colourize('abort', Colour.RED)
		}

	options_list = [f"{a} to {b}" for a, b in options.items()]

	return f"{colourize(command, Colour.YELLOW)}\n[{', '.join(options_list)}] "

class Command(object):
	whitelist = [
		# File and Directory Management
		"ls",        # List directory contents
		"cat",       # Concatenate and display file content
		"head",      # Display the beginning of a file
		"tail",      # Display the end of a file
		"find",      # Search for files in a directory hierarchy
		"which",     # Locate a command
		"stat",      # Display file or file system status
		"pwd",       # Print working directory
		"file",      # Filetype information

		# System Information and Status
		"uptime",    # Show how long the system has been running
		"ps",        # Report a snapshot of current processes
		"free",      # Display memory usage
		"who",       # Who is logged in
		"w",         # Who is logged in and what they are doing
		"date",      # Display or set the system date and time
		"cal",       # Display calendar information
		"hostname",  # Show the system hostname
		"uname",     # Show system information (kernel, architecture, etc.)
		"whoami",    # Show the current logged-in user
		"id",        # Show user and group information
		"pgrep",     # Search for processes by name
		"nproc",     # Display the number of processing units available
		"lsblk",     # List block devices
		"df",        # Filesystem disk space information
		"du",        # File size information
		"lscpu",     # CPU info
		"sw_vers",   # Prints macOS version information

		# File and Text Processing
		"grep",      # Search text using patterns
		"awk",       # Pattern scanning and processing language
		"cut",       # Remove sections from each line of files
		"wc",        # Word, line, character, and byte count
		"echo",      # Display a line of text
		"sed",       # Manipulate a stream of text

		# Networking and IP Configuration
		"ip",        # Show/manipulate routing, devices, policy routing, and tunnels
		"curl",      # Fetch and save date over a variety of different protocols
		"ping",      # Test internet connection status and latency
	]

	blacklist_flags = {
		"awk": [r"-d\w*", r"--dump-variables(?:=[0-9A-Za-z-_\\/.]*)?", r"-o\w*", r"--pretty-print(?:=[0-9A-Za-z-_\\/.]*)?"],
		"curl": ["-o", "--output", "-O", "--remote-name"],
	}

	def __init__(self, string):
		self.command = string
		self.commands = []

		# ???
		if isinstance(string, list):
			self.command = string[0]

		try:
			self.commands = re.split(r'&&|\|', self.command)
		except Exception as e:
			print(colourize(e, Colour.RED))
			sys.exit(1)

	def is_whitelisted(self):
		for command in self.commands:
			command = command.strip()
			parts = command.split(" ")
			executable = parts[0]

			if executable == "sudo":
				reason = f"You may not execute commands as superuser: '{command}'"
				return [False, reason]

			if executable not in self.whitelist:
				reason = f"You do not have permission to do that: '{executable}'"
				return [False, reason]

			if ">" in command or ">>" in command:
				reason = f"Redirecting to files is not permitted: '{command}'"
				return [False, reason]

			if executable in self.blacklist_flags:
				for option in parts[1:]:

					# Checks against blacklist and fails if present
					for flag in self.blacklist_flags[executable]:
						if re.match(flag, option) is not None:
							reason = f"Invocation of {executable} is using blocked flag: '{flag}'"
							return [False, reason]

		return [True, ""]

	def run(self):
		result = subprocess.Popen(self.command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		stdout = result.stdout.read()
		stderr = result.stderr.read()
		return [
			stdout.decode("utf-8"),
			stderr.decode("utf-8")
		]

	def __str__(self):
		return self.command


class Colour(Enum):
	RED = '31'
	GREEN = '32'
	YELLOW = '33'
	BLUE = '34'
	MAGENTA = '35'
	CYAN = '36'
	WHITE = '37'
	BLACK = '30'
	RESET = '0'

def colourize(text, colour):
	return f"\033[{colour.value}m{text}\033[{Colour.RESET.value}m"

if __name__ == '__main__':
	main()
