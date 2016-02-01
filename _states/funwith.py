def _get_prefix(name, prefix):
    from os.path import join
    return prefix if prefix is not None else \
        join(__pillar__['funwith']['workspaces'], name)

def _get_virtualenv(name, prefix, virtualenv):
    if virtualenv is None:
        return None
    if virtualenv is True:
        virtualenv = {}
    else:
        virtualenv = virtualenv.copy()
    if 'name' not in virtualenv:
        virtualenv['name'] = prefix
    return virtualenv

def _update_states(whole, parts):
    if (not __opts__['test']) and parts['result'] == False:
        whole['result'] = True
    whole['changes'].update(parts['changes'])
    if 'comment' in parts:
        whole['comment'] += "\n" + parts['comment']


def add_vimrc(name, source_dir=None, width=None, tabs=None,
              footer=None, makeprg=None, **kwargs):
    from os.path import join
    if width is None:
        width = __salt__['pillar.get']('vim:width', 100)
    if tabs is None:
        tabs = __salt__['pillar.get']('vim:tabs', 2)
    if makeprg is None and source_dir is not None:
        makeprg = __salt__['pillar.get'](
            'vim:makeprg', 'ninja\ -C\ {0}/build\ -v'.format(source_dir))
    defaults = {
        'prefix': name,
        'width': width,
        'tabs': tabs,
        'footer': footer,
        'makeprg': makeprg
    }
    defaults.update(**kwargs)
    return __states__['file.managed'](
        join(name, '.vimrc'),
        source='salt://funwith/vimrc.jinja',
        defaults = defaults,
        template='jinja'
    )


def add_cppconfig(name, prefix=None, source_dir=None, includes=None,
                  source_includes=None, cpp11=False, cpp=False, c99=False,
                  defines=None):
    from os.path import join
    if (cpp11 or cpp) and c99:
        raise RuntimeError("Cannot be both a c++ and c project")
    prefix = _get_prefix(name, prefix)
    lines = ["-Wall"]
    if includes is None:
        includes = []
    for include in includes:
        if len(include) == 0:
            continue
        if include[0] == "/":
          lines.append("-I" + include)
        else:
            lines.append("-I" + join(prefix, include))
    if source_includes is not None and source_dir is None:
        raise ValueError("Need source_dir to do source_includes")
    if source_includes is None:
        source_includes = []
    for include in source_includes:
        lines.append("-I" + join(source_dir, include))

    lines.append("-x")
    lines.append("c++" if cpp11 or cpp else "c")
    if cpp11:
        lines.append("-std=c++11")
    elif c99:
        lines.append("-std=c99")

    if defines is not None:
        lines.extend(["-D%s" % u for u in defines])

    return __states__['file.managed'](
        join(prefix, '.cppconfig'),
        contents='\n'.join(lines)
    )

def modulefile(name, prefix=None, cwd=None, footer=None, virtualenv=None,
               spack=None, modules=None, **kwargs):
    from subprocess import check_output
    from os.path import join, split
    prefix = _get_prefix(name, prefix)

    if modules is None:
        modules = []
    if spack is None:
        spack = []
    for package in spack:
        modules.extend(__salt__['spack.module_name'](package))

    virtualenv = _get_virtualenv(name, prefix, virtualenv)

    context = {
        'homedir': prefix,
        'srcdir': cwd,
        'footer': footer,
        'virtualenv': virtualenv,
        'modules': modules,
        'julia_package_dir': None
    }
    return __states__['file.managed'](
        join(__pillar__['funwith']['modulefiles'], name + ".lua"),
        source='salt://funwith/project.jinja.lua',
        template='jinja', context=context, **kwargs
    )

def present(name, prefix=None, cwd=None, github=None, srcname=None, email=None,
            username=None, footer=None, ctags=False, virtualenv=None,
            spack=None, vimrc=False, cppconfig=False, **kwargs):
    from os.path import join, split
    prefix = _get_prefix(name, prefix)
    if github is not None:
        if srcname is None:
            srcname = split(github)[1]
        target = join(prefix, 'src', srcname)
        if cwd is None:
            cwd = target

    # cwd can be relative to the prefix or absolute
    if cwd is None and len(cwd) == 0:
        cwd = prefix
    elif cwd is not None and cwd[0] != '/':
        cwd = join(prefix, cwd)

    result = {
        'name': name,
        'changes': {},
        'result': None if __opts__['test'] else True,
        'comment': ''
    }
    if spack is not None:
        pkgs = __states__['spack.installed'](spack)
        _update_states(result, pkgs)

    virtualenv = _get_virtualenv(name, prefix, virtualenv)
    if virtualenv is not None:
        virtualenv.update(kwargs)
        virtenv = __states__['virtualenv.managed'](**virtualenv)
        _update_states(result, virtenv)

    mfile = modulefile(name, prefix=prefix, cwd=cwd, footer=footer,
                       spack=spack, **kwargs)
    _update_states(result, mfile)
    if prefix is not None:
        dir = __states__['file.directory'](prefix)
        _update_states(result, dir)
    if cwd is not None and cwd != prefix and cwd != target:
        dir = __states__['file.directory'](cwd)
        _update_states(result, dir)
    if github is not None:
        vcs =  __states__['github.present'](github, email=email,
                                            username=username, target=target)
        _update_states(result, vcs)
        if ctags:
            ctag = __states__['ctags.run'](target, exclude=['.git', 'build'])
            _update_states(result, ctag)

    if vimrc:
        args = vimrc.copy() if isinstance(vimrc, dict) else {}
        vim = add_vimrc(
                join(prefix, name), source_dir=target, cppconfig=cppconfig,
                **args
            )
        _update_states(result, vim)

    if cppconfig:
        args = cppconfig.copy() if isinstance(cppconfig, dict) else {}
        cpp = add_cppconfig(name, prefix=prefix, source_dir=target, **args)
        _update_states(result, cpp)

    return result
