#!/usr/bin/env bash

set -o nounset
set -o errexit

## update list of available packages
apt-get -qq update || {
    echo "failed updating list of available packages"
    exit 1
}

## enable snap packages: https://snapcraft.io/
apt-get install -y snapd || {
    echo "failed enabling snap packages"
    exit 1
}

## install hugo: https://gohugo.io/
snap install hugo || {
    echo "failed installing hugo"
    exit 1
}

# /home/travis/.rvmrc
# rvm_autoupdate_flag='0'
# rvm_binary_flag='1'
# rvm_fuzzy_flag='1'
# rvm_gem_options='--no-ri --no-rdoc'
# rvm_max_time_flag='5'
# rvm_path='/home/travis/.rvm'
# rvm_project_rvmrc='0'
# rvm_remote_server_type4='rubies'
# rvm_remote_server_url4='https://s3.amazonaws.com/travis-rubies/binaries'
# rvm_remote_server_verify_downloads4='1'
# rvm_silence_path_mismatch_check_flag='1'
# rvm_user_install_flag='1'
# rvm_with_default_gems="rake bundler"
# rvm_without_gems="rubygems-bundler"

## set up rvm environment
#. $HOME/.rvmrc

#rvm_path='/home/travis/.rvm'

#(rvm_path='/home/travis/.rvm'; echo "$rvm_path/scripts/rvm"; cat "$rvm_path/scripts/rvm") || {
#    echo "$rvm_path/scripts/rvm DOES NOT EXIST"
#}

## add rvm bin directory to path
#PATH=${PATH:+${PATH}:}$HOME/.rvm/bin
#export PATH

## use rvm default ruby
rvm use default || {
    echo "failed setting up ruby environment"
    exit 1
}

## install HTMLProofer
NOKOGIRI_USE_SYSTEM_LIBRARIES=true gem install --source https://rubygems.org html-proofer || {
    echo "failed installing HTMLProofer"
    exit 1
}

exit 0
