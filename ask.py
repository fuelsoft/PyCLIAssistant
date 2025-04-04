#! /bin/env python

# LLM-based command line assistant

import os
import sys
import json
import platform
from enum import Enum
from datetime import datetime

import Prompts
from Command import Command
from PyLLMAdapter.Ollama import Ollama

REQ_CONFIRM = True
DEBUG = False

# If you are not running locally, change these values
# Codestral is the model I've tested against and what the prompts below are tuned for
ol = Ollama(model = "codestral", ip = "localhost", port = 11434)

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

# usage: ask.py <question>
def ask(prompt):
	current_time = datetime.now()
	formatted_time = current_time.strftime("%Y/%m/%d %H:%M:%S")
	message = Prompts.ask_prompt.format(shell = SHELL, platform = PLATFORM, datetime = formatted_time, prompt = prompt)

	reply = ol.chat(message, temperature = 0.3)
	output = handle_reply(reply)

	while output is not None:
		stdout = output[0]
		stderr = output[1]

		# normally the temperature should be low - we don't want the model to get creative when summarizing the results
		# however, if there's error output, it may be better to set the temperature higher to encourage outside-the-box thinking on a workaround
		temperature = 0.3
		if len(stderr) > 0:
			temperature = 0.8

		message = Prompts.ask_reply.format(shell = SHELL, stdout = stdout, stderr = stderr, prompt = prompt)
		if DEBUG: print(message)

		reply = ol.chat(message, temperature = temperature)
		output = handle_reply(reply)

def handle_reply(reply):
	try:
		action = reply.json()
	except Exception as e:
		print("Failed to parse reply JSON!")
		print(reply.message)
		raise

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
					return

				if user_input == "?":
					print(colourize("Explaining...", Colour.CYAN))
					reply = ol.ask(Prompts.ask_explain.format(shell = SHELL, command = command))
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

def colourize(text, colour):
	return f"\033[{colour.value}m{text}\033[{Colour.RESET.value}m"

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

if __name__ == '__main__':
	ask(sys.argv[1])
