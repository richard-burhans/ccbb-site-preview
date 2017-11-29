#!/usr/bin/env sh

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

(echo "/etc/rvmrc"; test -e /etc/rvmrc) || {
    echo "/etc/rvmrc DOES NOT EXIST"
}

(echo "/etc/profile.d/rvm.sh"; test -e /etc/profile.d/rvm.sh) || {
    echo "/etc/profile.d/rvm.sh DOES NOT EXIST"
}

(echo "$HOME/.rvmrc"; test -e $HOME/.rvmrc) || {
    echo "$HOME/.rvmrc DOES NOT EXIST"
}

## add rvm bin directory to path
PATH=${PATH:+${PATH}:}$HOME/.rvm/bin
export PATH

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
