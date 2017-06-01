#!/usr/bin/env python

import click
import subprocess
from tempfile import NamedTemporaryFile, mkdtemp
import os
import re
import logging
import haml
import mako.template
import codecs

logger = logging.getLogger(os.path.dirname(__file__))
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.WARN)

from pyutils.file import open_or_stdout

HTML2HAML_PATH = '/usr/local/var/rbenv/shims/html2haml'
HAML_PATH = '/usr/local/var/rbenv/shims/haml'

doublestar_to_kwargs = r'("(\w+?)"\:\s([^\,\}]*))'
hash_to_kwargs = r'"?(([\-\w]*?)"?\s=>\s(\d+|".*?"))'
h2kw = r'"?(\:)?([\-\w]*?)"?\s=>\s(\d+|".*?")(, )?'
dash_in_key = r'(\"[\w\-]*\"\s=>)'

def _pythonize(ruby_haml):
    "Convert html2haml-generated HAML to PYHAML"
    brackets_patt = r'(\{)(?=(.*?\s?\=\>))(.*?)(\})'
    search_patt = r'(\"|\:)(.*?)\"?\s\=\>\s([^\,\}]*)'
    repl_patt = r'"\2": \3'
    repl_patt_2 = r'\2=\3'

    # logger.debug("before:\n{0}\n".format(ruby_haml))
    ruby_haml = ruby_haml.decode('utf-8')

    # Look for rockets inside brackets (html2haml generates old-school hashes)
    matches = re.finditer(brackets_patt, ruby_haml, re.MULTILINE)
    # logger.debug([m[2] for m in matches])
    for match in matches:
        # logger.debug("---")

        # We prefer keyword arguments, but if a key contains dashes...
        if re.search(dash_in_key, match.group(3)):
            # logger.debug("{0} matched...".format(match.group(3)))

            # we can only convert to (**{'key': value})...
            repl = match.expand(r'(**\1\3\4)')
            # logger.debug("...expanding to {0}...".format(repl))

            # replacing hashrockets with colons
            repl = re.sub(search_patt, repl_patt, repl)
            # logger.debug("...changing to {0}".format(repl))
        else:
            # logger.debug("{0} didn't match...".format(match.group(3)))

            # With no dashes in a key we can replace
            # brackets (Ruby HAML) with parens (PyHAML)...
            repl = match.expand(r'(\3)')
            # logger.debug("...expanding to {0}...".format(repl))

            # and use keyword arguments in concordance with natural law:
            # (key=value, key2=value2)
            repl = re.sub(search_patt, repl_patt_2, repl)
            # logger.debug("...changing to {0}".format(repl))

        # This match by agonizing match solution has been brought to
        # you by re's omission of recursing capture groups
        ruby_haml = ruby_haml.replace(match.group(0), repl, 1)

    return ruby_haml

def _run_ruby_executable(ruby_executable_path, input):
    if not os.path.isfile(input):
        logger.debug("Sending from stdin...")
        subprocess_args = [ruby_executable_path]
        p = subprocess.Popen(
            subprocess_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output, err = p.communicate(input)
    else:
        subprocess_args = [ruby_executable_path, input]
        output = subprocess.check_output(subprocess_args)
    return output

def convert(input, output_file=None, from_format="html", to_format="pyhaml"):
    logger.debug("convert got input {}; from {}, to {}"
        .format(input, from_format, to_format))

    if (from_format, to_format) == ("html", "haml"):
        output = _run_ruby_executable(HTML2HAML_PATH, input)
    elif (from_format, to_format) == ("html", "pyhaml"):
        haml_output = _run_ruby_executable(HTML2HAML_PATH, input)
        output = _pythonize(haml_output)
    elif (from_format, to_format) == ("haml", "pyhaml"):
        output = _pythonize(input)
    elif (from_format, to_format) == ("haml", "html"):
        output = _run_ruby_executable(HAML_PATH, input)
    elif (from_format, to_format) == ("pyhaml", "html"):
        template = mako.template.Template(input,
            preprocessor=haml.preprocessor)
        output = template.render()
    else:
        return None

    with open_or_stdout(output_file) as f:
        try:
            output = codecs.decode(output, 'utf-8')
        except TypeError:
            pass # unicode by default in Python 3
        f.write(output)


choices = ('haml', 'html', 'pyhaml')

@click.command()
@click.option('from_format', '-f', '--from', type=click.Choice(choices), default='html')
@click.option('to_format', '-t', '--to', type=click.Choice(choices), default='pyhaml')
@click.option('--output-file', '-o', default=None, type=click.File('w'))
@click.argument('input', required=False, default=None)
def cli(from_format, to_format, output_file, input):
    if from_format == to_format:
        click.echo("--from format is the same as --to format; exiting")
    else:
        if input is None:
            logger.debug("Reading stdin...")
            input = click.get_text_stream('stdin').read()
        convert(input, output_file, from_format, to_format)



