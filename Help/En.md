# MiTerm-N5 Help

## General description

MiTerm-N5 is a terminal application that can be used with a screen reader.
The goal is not to provide a universal terminal, but rather:
- to use command-line applications (CLI) comfortably;
- to make programs in terminal mode (TUI) easier to use;
- to allow following a progress or an update of a result;
- to be able to select and confirm a choice with the keyboard;
- to read and browse the output of programs freely, whatever the pace at which it is displayed;
- to keep a history, which allows going back to the information displayed earlier.

## Session

A session is a set of settings defined in the window of the application.
It is limited to running one program at a time, but it is possible to open several application windows.

Before you run a program, you choose its mode.
The CLI mode suits most commands: the program reads and writes text.
The TUI mode suits programs that need a real terminal: python, ssh, passwords.
The mode is chosen by the user, never guessed.

You can also select an interpreter, Cmd or PowerShell.
A shell is always in TUI mode.

The working folder is the one where the program starts.
You can change it as long as no program is running.

## Profile

A profile stores the settings of a program that you use often.
It contains the program, the mode, the interpreter, the size of the terminal and a list of common commands.
With a program, the common commands no longer have to repeat it: `status` is enough for `git status`.
The list says only the name of the program, and the command field receives the full path.

You choose a profile yourself.
MiTerm-N5 never applies one on its own.
With no profile chosen, the session is "Free".

The common commands of a profile are added to the list of typed commands.
They can contain variables, written between braces: `{name}`, `{source}`, `{destination}`, `{value1}`, `{value2}`, `{comment}`, `{ip}`, `{message}`.
You give their value in the variables dialog, and they replace the braces in the list.

A `git` profile is provided as an example.
You can add, edit and delete your profiles.
Each profile is a small file: you can copy it to another computer.

## Using the application
The window has three parts:
+ An output area, at the top: you read what the program writes in it.
+ A command area, at the bottom: you type a command in it, then Enter to send it.
+ A status bar, showing the line, the column and the state of the program.

### Running and following a program

Type the command in the command field, then Enter.
The focus moves automatically to the output area, on the line of the command.
To send other commands, you must go back to the command area.
Some keys or keyboard shortcuts can be sent directly to the program from this area.

The end of the program is announced with its exit code.

### Command area

The label of the input field tells how the text is used:
- Command: the text is a command. At rest, it runs a program; in an open shell (Cmd, PowerShell) or with a connection, it is sent to the shell.
- Message: the text is sent as is to the running program (an answer to a question, for example).
- The name of the profile ("Git"): the text becomes the arguments of the profile's program, which is run when you send it. So an empty field runs the program alone.

A history of the last commands, as well as the commands of the profile, can be brought up from this input field.

The check box that masks the typed text is cleared automatically after a send.
A masked text is not stored in the history.

The main input field can contain only one line.
To send several lines, use the multi-line input box.

### Output area

The output arrives silently:
- The text that is added or changed is not announced;
- neither the focus nor the text caret is changed;
- you read when you decide to.
- the oldest messages are found by going up in the text.

Reading and searching the content are done with the usual keys.
However, some features can make browsing the content easier:
- moving from heading to heading, especially for the CMD and PowerShell profiles.
- help to identify some elements, such as progress bars, choices, links, ...
- comfortable reading, by limiting redundant texts. By default the common command prompts, but you can add other detection patterns.

The output of programs in error starts with "StdErr:": it is recognized by its text, not by its color.

#### Interactive programs

In TUI mode, you can send the program keys that the command field does not pass on: arrows, Esc, Tab, function keys.
This is useful for menus and lists of choices.
The Session menu offers these keys, and you can give them a shortcut.

The terminal cursor is where the program waits for your input.

#### Activities

Many programs write progress bars, ask a question or show a choice.
MiTerm-N5 recognizes these elements in the lines of the output.
It recognizes progress, questions, choices and errors.

Three functions rely on this recognition.
Read the line with formatting says the line of the text caret more clearly: "Download, 60 %".
Identify activities lists what is recognized on the screen, and takes you to the line you choose.
Signal activities warns you when the output changes.

The activity signal is set in the Preferences, on the Announcements page.
By default, MiTerm-N5 checks every second whether the output has changed.
If the line of the caret is a recognized element, it says it.
Otherwise, it plays a beep, to signal a change.
If the beep bothers you, turn the signal off with a shortcut.

### Status bar and announcements

MiTerm-N5 announces only what matters: the start and end of a program, errors, refused commands.
You can choose, for each category, whether it is said, ignored or shown in a dialog box.

The status bar has three information fields:
- Position of the line
- state of operation
- Position of the column

## Connection

A connection defines where what you run is executed: on this computer, or on a server.
- "Local" is the default choice: programs run on this computer.
- The other choices are connections to servers.
When a connection is chosen, all commands are sent to its server.
The working folder, the interpreter and the mode are therefore no longer available.
Sending a command automatically opens a connection.

### SSH

By default, MiTerm-N5 uses the OpenSSH ssh.exe program, which comes with Windows.
Authentication can be done in two ways.
+ By password: a dialog box shows the server and asks for the password, in a masked field.
+ By key: ssh finds your key by itself and asks no question.

The first time you connect to a server, ssh shows its fingerprint and asks whether you trust it.
Cancelling a dialog is not an error: the connection simply stops.
MiTerm-N5 keeps no password and copies no key.

Where the keys are:
- The server key, the one you accepted, is written by ssh in the `known_hosts` file of the `.ssh` folder of your Windows profile (`%USERPROFILE%\.ssh\known_hosts`).
  In portable mode, it is in the `data\known_hosts` file, next to the application.
- Your private key is a file in the same `.ssh` folder, for example `id_ed25519`, next to its public key `id_ed25519.pub`, the one you copy to the server.
  Never share the private key.
  The `ssh-keygen` profile can help you create it.

## Usage limits

- MiTerm-N5 works only on Windows.

- It does not run graphical programs, which open their own window.
- It does not support full-screen programs such as `vim` or `htop`.
They start, but their screen is not read as a grid.
The keyboard is not passed to them directly.

- The output has a limit on the number of lines, which can be set in the Preferences.
The oldest lines are dropped, and MiTerm-N5 tells you so.

- An export may contain secrets: read it again before sharing it.

- A line longer than the screen is read as several lines, as in an ordinary terminal.
MiTerm-N5 then enlarges the terminal if you chose the automatic size.

- The recognition of activities reads the text, not the colors.
It can be wrong or see nothing.
A password that is typed writes nothing: the question is still recognized after the answer.

- A program that is run keeps the rights of the user.
MiTerm-N5 does not protect against a dangerous command.

## Launch file (.n5term)

A file with the `.n5term` extension opens a session that is already set up.
You only have to pass it to the application, or double-click it, after an association.
The association button in the Preferences, General page, makes MiTerm-N5 open these files.

It is a text file, with one key and its value per line.
Lines that start with `;` or `#` are comments.

The required key:
- `profile`: the name of the profile to choose.

The other possible keys are:
- `WorkingPath`: the working folder;
- the name of a variable of the profile (`name`, `source`, `comment`, `message`…): its value.

Example:
```
profile = git
WorkingPath = C:\Projects\my-project
source = origin
```

If no value is set for `WorkingPath`, the session starts in the folder of the file.
A relative path is read from that folder.

The file runs no command.

## Local mode and portable mode

In local mode, MiTerm-N5 stores its data in your Windows profile.
The settings and the profiles are in `%APPDATA%\MiTerm-N5`.
The log is in `%LOCALAPPDATA%\MiTerm-N5\Logs`.

The portable mode suits a USB key.
It leaves no trace on the host computer.
Settings, profiles and log are in a `data` folder, next to the executable.

To switch to portable mode, put an empty file named `portable` next to the executable.
You can also specify a data folder with the `--data-folder` option.
