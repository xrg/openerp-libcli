# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright 2011 P. Christeas
#    Author (blame me): P. Christeas <xrg@hellug.gr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


#.apidoc title: Standardized Options+Config parser for client scripts

""" Since most of the client scripts may need the same set of parameters,
    put them all in this common configuration utility

    Usage::

        import logging
        from openerp_libclient.extra import options

        options.init(...)

        logging.getLogger('ham').info('spam!')
        for filename in options.args():
            spam(filename)
"""

from ConfigParser import SafeConfigParser, NoSectionError
import optparse
import sys, os
import logging
import re

opts = args = None
config_stray_opts = []
allow_include = 0 #: integer, 0 doesn't allow, or levels of include to permit

connect_dsn = {'proto': 'http', 'user': 'admin', 'host': 'localhost', 'port': 8069,
        'dbname': 'test'}

log_section = 'libcli.options'

_non_options = ['configfile', 'config_section', 'have_config', 'include']
_list_options = {} #: Options that must be parsed as a list. optname: key pairs
_path_options = ['homedir', 'logfile',] #: options that must be path-expanded

def _parse_option_section(conf, items, copt, opt, _allow_include=0):
    """ Parse a .conf file section into `opt`

        @param conf the Config object
        @param items the items section of that config file
        @param copt the optparse options
        @param opt copy of the optparse options, that will receive values
        @param _allow_include levels of recursive include to allow
    """
    global config_stray_opts, _non_options, _list_options, _path_options

    for key, val in items:
        if key == 'include' and _allow_include:
            for inc in val.split(' '):
                _parse_option_section(conf, conf.items(inc), copt, opt, _allow_include=(_allow_include-1))

    for key, val in items:
        if key in _non_options:
            continue
        elif key in dir(copt):
            if key in _list_options:
                val = val.split(_list_options[key])
            elif isinstance(getattr(copt, key), list) or \
                    (key in ('modules',)):
                val = val.split(' ')
            elif isinstance(getattr(copt, key), bool):
                val = bool(val.lower() in ('1', 'true', 't', 'yes'))

            if not getattr(copt, key):
                setattr(opt, key, val)
        else:
            config_stray_opts.append((key, val))
            pass


def _parse_url_dsn(url, connect_dsn):
    import urlparse
    netloc_re = re.compile( r'(?:(?P<user>[^:@]+?)(?:\:(?P<passwd>[^@]*?))?@)?'
        r'(?P<host>(?:[\w\-\.]+)|(?:\[[0-9a-fA-F:]+\]))'
        r'(?:\:(?P<port>[0-9]{1,5}))?$')
    uparts = urlparse.urlparse(url, allow_fragments=False)

    if uparts.scheme:
        connect_dsn['proto'] = uparts.scheme
    if uparts.netloc:
        um = netloc_re.match(uparts.netloc)
        if not um:
            raise ValueError("Cannot decode net locator: %s" % uparts.netloc)
        for k, v in um.groupdict().items():
            if v is not None:
                connect_dsn[k] = v
    if uparts.query:
        pass
    if uparts.path and len(uparts.path) > 1:
        connect_dsn['dbname'] = uparts.path.split('/')[1]
    # path, params, fragment

def init(usage=None, config=None, have_args=None, allow_askpass=True,
        options_prepare=None, defaults=None, config_section='general', post_conf=None):
    """

        @param usage a string describing the usage of the script
        @param config a string or list of filenames to use as default
            configuration files. Remember, the '-c' option overrides them
        @param have_args policy about non-option arguments:
            True means at least one must exist
            False means no arguments are allowed
            None means don't care
            int means exactly that many arguments must be present
        @param allow_askpass ask for a password at the standard console,
            if no password is specified at url or config file
        @param options_prepare a callable that will add any initial options
            to the OptionParser
        @param defaults defaults, fallback for standard options
        @param config_section The config section to use from the file, *or*
            tuple with arguments to ask the section from. If empty tuple '()'
            is given, defaults to ('-s', '--config-section')
        @param post_conf A function, to call with SafeConfigParser as an argument,
            after all of the configuration is read. Useful to parse custom sections
            apart from the ones included

        Example of options_prepare::

            def custom_options(parser):
                assert isinstance(parser, optparse.OptionParser)

                pgroup = optparse.OptionGroup(parser, "My options")
                pgroup.add_option('--foo')
                parser.add_option_group(pgroup)

            ...
            options.init(..., options_prepare=custom_options)

            if options.opts.foo:
                do_foo()
    """
    global connect_dsn, log_section
    global opts, args
    parser = optparse.OptionParser(usage or "%prog [options]\n")

    if options_prepare:
        options_prepare(parser)

    pgroup1 = optparse.OptionGroup(parser, 'Standard Client Options',
                    "These options define the connection parameters "
                    "to the remote OpenERP server and debugging control.")

    pgroup1.add_option("-H", "--url", default=None,
                        help="URL of remote server to connect to"),
    pgroup1.add_option("-v", "--verbose", "--debug", dest="debug", action='store_true', default=False,
                        help="Enable detailed log messages")
    pgroup1.add_option("--quiet", dest="quiet", action='store_true', default=False,
                        help="Print only error messages")

    pgroup1.add_option("--log", dest="logfile", help="A file to write plain log to, or 'stderr'")
    pgroup1.add_option("--log-format", dest="log_format", help="Default formatting for log messages")

    pgroup1.add_option("--password", dest="passwd", help="specify the User Password." \
                        "Please don't use this, security risk.")
    pgroup1.add_option("-P", "--passwd-file", default=None, help="read the password from that file (safer)")

    if allow_askpass:
        pgroup1.add_option("--ask-passwd", dest="ask_passwd", action="store_true", default=False,
                        help="Ask for passwords with an interactive prompt"),

    pgroup1.add_option("-d", "--database", dest="dbname", help="specify the database name")


    pgroup2 = optparse.OptionGroup(parser, 'Config-File options',
                    " These options help run this script with pre-configured settings.")

    pgroup2.add_option("-c", "--config", dest="configfile",
                help="Read configuration options for this script from file. ")
    pgroup2.add_option("--no-config", dest="have_config", action="store_false", default=True,
                help="Do not read the default config file, start with empty options.")

    if isinstance(config_section, tuple):
        kwcfs = dict(dest="config_section", default="general",
                help="Use that section in the config file")
        if not config_section:
            config_section = ('-s', '--config-section')
        pgroup2.add_option(*config_section, **kwcfs)
        del kwcfs

    parser.add_option_group(pgroup1)
    parser.add_option_group(pgroup2)

    (copt, args) = parser.parse_args()

    # Now, parse the config files, if any:
    opts = optparse.Values(copt.__dict__)

    if isinstance(config_section, tuple):
        config_section = copt.config_section

    conf_read = False
    cfgparser = False
    if copt.have_config:
        if copt.configfile:
            cfiles = [copt.configfile,]
        elif isinstance(config, basestring):
            cfiles = [config,]
        else:
            cfiles = config

        if cfiles:
            cfiles = map(os.path.expanduser, cfiles)
            cfgparser = SafeConfigParser()
            conf_filesread = cfgparser.read(cfiles)
            try:
                _parse_option_section(cfgparser, cfgparser.items(config_section),
                            copt, opts, allow_include)
                conf_read = True
            except NoSectionError:
                conf_read = False
                pass

    # Apply defaults to empty options
    if defaults:
        for key, val in defaults.items():
            if not getattr(opts, key):
                setattr(opts, key, val)

    # Expand any path options
    for key in _path_options:
        if getattr(opts, key, None):
            setattr(opts, key, os.path.expanduser(getattr(opts, key)))

    # Then, analyze the URL
    if opts.url:
        _parse_url_dsn(opts.url, connect_dsn)

    # initialize logging
    log_kwargs = dict(level=logging.INFO)
    if opts.debug:
        log_kwargs['level'] = logging.DEBUG
    elif opts.quiet:
        log_kwargs['level'] = logging.WARN

    if opts.logfile and opts.logfile != 'stderr':
        log_kwargs['filename'] = os.path.expanduser(opts.logfile)
    if opts.log_format:
        log_kwargs['format'] = opts.log_format
    logging.basicConfig(**log_kwargs)

    _logger = logging.getLogger(log_section)
    if conf_read:
        _logger.info("Configuration read from %s", ','.join(conf_filesread))
    else:
        if copt.configfile:
            _logger.warning("Configuration could not be read from %s", copt.configfile)

    # enforce the arguments policy
    if have_args is not None:
        if have_args is True:
            if not args:
                _logger.error("Must supply at least one argument")
                sys.exit(1)
        elif have_args is False and args:
            _logger.error("No arguments are allowed to this sript")
            sys.exit(1)
        elif len(args) != int(have_args):
            _logger.error("Must supply %s args, %d given", have_args, len(args))
            sys.exit(1)

    # Get the password
    if opts.ask_passwd:
        import getpass
        connect_dsn['passwd'] = getpass.getpass("Enter the password for %s@%s: " % \
            (connect_dsn['user'], connect_dsn['dbname']))
    elif opts.passwd:
        connect_dsn['passwd'] = opts.passwd
    elif opts.passwd_file:
        try:
            fp = open(opts.passwd_file, 'rb')
            connect_dsn['passwd'] = fp.readline().strip()
            fp.close()
            # file name is deliberately hidden
            _logger.debug("Password read from file")
        except Exception, e:
            _logger.warning("Password file could not be read: %s", e)
    
    if post_conf:
        post_conf(opts, args, cfgparser)

#eof