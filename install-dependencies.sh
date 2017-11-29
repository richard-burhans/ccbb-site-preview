#!/usr/bin/env bash

set -o nounset
set -o errexit

## update list of available packages
echo "INFO: updating list of available packages"
apt-get -qq update || {
    echo "ERROR: failed updating list of available packages"
    exit 1
}

## enable snap packages: https://snapcraft.io/
echo "INFO: enabling snap packages"
apt-get install -y snapd || {
    echo "ERROR: failed enabling snap packages"
    exit 1
}

## install hugo: https://gohugo.io/
echo "INFO: installing hugo"
snap install hugo || {
    echo "ERROR: failed installing hugo"
    exit 1
}

## set up rvm environment: https://rvm.io/
echo "INFO: setting up rvm environment"
source "$HOME/.rvmrc"
set +o nounset
source "$rvm_path/scripts/rvm"
set -o nounset
export PATH="${PATH:+${PATH}:}$rvm_bin_path"

## use rvm default ruby
rvm use default || {
    echo "ERROR: failed setting up ruby environment"
    exit 1
}

## install HTMLProofer
echo "INFO: installing HTMLProofer"
NOKOGIRI_USE_SYSTEM_LIBRARIES=true gem install --source https://rubygems.org html-proofer || {
    echo "ERROR: failed installing HTMLProofer"
    exit 1
}

exit 0
