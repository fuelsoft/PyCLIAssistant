#! /bin/env python

import re
import subprocess

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
