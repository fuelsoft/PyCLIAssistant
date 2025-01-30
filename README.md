# PyCLIAssistant

## A simple LLM-based command line assistant

This is a small program that connects to an Ollama instance to turn a natural language question into an answer.

### An important note about LLMs and your system

**Do not, under any circumstance, allow any LLM to execute arbitrary commands on your system.**

If you are not willing or not able to supervise the LLM backing this program, do not download or run this program. If the model goes rogue and decides that only thing to do is `rm -rf /`, I will not be to blame.

All that being said, there are a number of safety measures in place:

* The LLM is asked not to issue destructive commands
* The program ships with a preset whitelist of "commands that I'm pretty sure are safe to run"
* The program makes an effort to find "hidden" commands - pipes, `sudo`, output redirection
* Every command is presented to the user for approval before being executed, with the option to exit immediately

### Usage

The basic control flow of the program is:

1. Get input
2. Ask LLM
3. If answered, exit
4. User confirmation of command
5. Run command
6. Return output to LLM
7. GOTO 2

When asked for confirmation, you'll see something like this:

```
$ ./ask.py "who's logged in on this system?"            <- command line invocation
who                                                     <- suggested command
[Enter to run, ? to explain, ^C to abort]               <- your options
Running command...                                      <- confirmation of selection

The user 'nick' is currently logged in on this system.  <- command result (as summarized by the LLM)
```

#### Run

Your options may say "Enter to run" if the command(s) are all on the whitelist:

![Run suggested command](/images/run.png)

Or you might see "Enter to retry / F to bypass safety" if one or more safety conditions are not met:

![Bypass safety checks](/images/bypass.png)

Hitting enter will cause the command to fail and the reason will be sent to the LLM. There is no guarantee that this will cause it to try again - in my experience it's about 50/50.

A suggestion not passing the safety checks is not necessarily an immediate concern - I might have missed a command, or it might be trying to innocently create a file that you asked for. However, any time that you're considering bypassing the safety checks, **please make sure you read and understand what the command is doing**.

#### Explain

If you type `?` in at the prompt and hit enter, the program will ask the LLM to examine its suggestion and explain. This is done *without the context of the preceding conversation* - that is to say, the LLM will not remember who wrote the command or what the original question was, and will have to examine the command as-is. This is sort of a "second opinion" check and is generally quite helpful.

![Explain suggested command](/images/explain.png)

Once the explanation is printed, you will be returned to the previous prompt.

#### Quit

If for any reason you want to exit and not run the command, you can hit Control-C to exit and the suggested command will not be run.

![Quit program](/images/quit.png)
