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

## use rvm to setup a ruby environment: https://rvm.io/
set +o nounset
set +o errexit

echo "INFO: setting up rvm environment"
source "$HOME/.rvmrc"
source "$rvm_path/scripts/rvm"
export PATH="${PATH:+${PATH}:}$rvm_bin_path"
echo "INFO: finished setting up rvm environment"

echo "INFO: changing to rvm default ruby"
rvm use default
echo "INFO: finished changing to rvm default ruby"

set -o nounset
set -o errexit

## install HTMLProofer
echo "INFO: installing HTMLProofer"
NOKOGIRI_USE_SYSTEM_LIBRARIES=true gem install --source https://rubygems.org html-proofer || {
    echo "ERROR: failed installing HTMLProofer"
    exit 1
}

exit 0
