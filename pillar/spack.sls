spack:
  add_to_zprofile: True
  compilers_file: salt://files/spack/compilers.yaml
  external_packages: salt://files/spack/packages.yaml
  repos:
      UCL-RITS: UCL-RITS/spack_packages

  # directory: {{grains['userhome']}}/spack
  # config_dir: {{grains['userhome']}}/.spack
  # default_config_location: user
  # repo_prefix: {{grains['userhome']}}/.spack_repos
