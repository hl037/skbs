# Welcome to SKBS

SKBS means SKeleton BootStrap.

SKBS is a powerful template engine, that can be used on a wide range of tasks, from project boilerplate bootstrap to Code generation.

Thanks to Tempiny, skbs provides a template syntax that is just Python code, avoiding the need for learning yet another language.

Moreover, contrary to other template language, it is possible to change the delimiters to avoid the need for escaping.

# Features

  * Turing complete
  * Easy to create, install, use, and share templates
  * Section to keep user edits on a previously generated file
  * Dynamic file and directory names
  * In-template Click integration to provide quickly user-friendly CLI-like options 
  * Heavily tested with `pytest`

# Install

`pip` is the preferred way. Then you should generate the configuration (simply where the template are installed...)

By default, the config in installed at the default location  for user configs (`~/.local/config/skbs/` for unix-like)

```
pip install skbs
skbs create-config
```

Then, you can "install" the default templates (`skbs` and `skbs.sft`) that come with skbs (they are the boilerplate to create templates).

I recommend you to read the Tutorial ( https://github.com/hl037/skbs/wiki/Tutorial ) for a friendly introduction to all skbs features, and API_Reference ( https://github.com/hl037/skbs/wiki/API_Reference ) if you need further details

# Usage

```
Usage: skbs [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config PATH  Overide the default configuration path
  --help             Show this message and exit.

Commands:
  config-path       Prints the path to the in-use configuration file.
  create-config     Create / reset to default the configuration file.
  gen               Generate a skeleton from a template.
  install           Install a new template.
  install-defaults  Install default provided templates
  list              List installed templates.
  uninstall         Uninstall a template uninstall         Uninstall a template
```

Usage of `skbs gen`

```
Usage: skbs gen [OPTIONS] TEMPLATE DEST [ARGS]...

  Generate a skeleton from a template.

  template : if template starts with an '@', it will look for an installed
  template. Else, it will be considered as the template path. dest : the
  output directory (parents will be created if needed) args : argument passed
  to the template ( skbs gen <template_name> -- --help for more informations )

Options:
  -g, --debug
  --stdout           Only for single file templates : output to stdout.
                     --single-file is implied
  -s, --single-file  Authorize single file template for non installed
                     templates.
  --help             Show this message and exit.
```

# (Very) Quick start

This section will cover only the very basic, without too much explanation, see it only as a cheat sheet. Read the full Tutorial ( https://github.com/hl037/skbs/wiki/Tutorial ) to leverage the full potential of SKBS.

You may also find the API_Reference ( https://github.com/hl037/skbs/wiki/API_Reference ) useful

------

Install the default-provided templates :
```
skbs install-default
```

To request a template's help, use `@help` as destination (or pass `--help` as first template argument, after the `--`:

```
skbs gen @skbs.sft @help
#or
skbs gen @skbs.sft foo_bar -- --help
```
------

To create a self-contained single file template:
```
skbs gen @skbs.sft my_template -- -c
```

Where `my_template` is the name you want to give it.
Edit my template.

Any file starting with a line :
```
## # {{__skbs_template__}}
```

Is considered a dynamic file, with python support. If this line is not present, it is considered a raw file and is copied as is.

Every line starting with `##` are python, and are not output. Indent level increments on lines ending with `:`, and decrements on line containing a single `-`.

Other lines are printed as they are (possibly multiple time if the python execution flow reach them again).

`{{` and `}}` in a normal line delimit a python expression. It is evaluated and its result replaces the whole `{{...}}` pattern.

This syntax can be changed by modifying the header line as described in the Tutorial ( https://github.com/hl037/skbs/wiki/Tutorial ).

------

To create a multi-file template :
```
skbs gen skbs my_second_template -- -c
```

Where `my_second_template` is the name of the template.

Inside `my_second_template`, `plugin.py` is the entry point where you can parse the `args` user-provided argument after the `--`.

The content of the `root` directory will be put inside the destination the user provided, each file will be checked for a template header line, and if found, will be parsed and executed as for the self-contained single file template.

------

To install a template (or a directory containing template :

```
skbs install -s my_template -n <name>
```

Where `<name>` should be replaced by the name you want to use to recall the template.

------

You can list installed template with :

```
skbs list
```
------

...Then you can recall any template in this list using :
```
skbs gen @<name> [...]
```
Where `<name>` is a line that appear in `skbs list`.

