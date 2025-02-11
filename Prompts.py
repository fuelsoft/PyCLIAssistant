#! /bin/env python

ask_prompt = """
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

ask_reply = """
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

ask_explain = """
Explain the following command(s):

```{shell}
{command}
```

Explain what all parameters and flags do, if any are specified.
If this could result in any side-effects, make note of them.
"""
