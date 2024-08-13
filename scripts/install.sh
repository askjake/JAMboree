#!/bin/bash

# adds env scripts to ~/.bashrc
# uses current location of scripts and adds it to PATH in .bashrc

script_location=$(dirname $(pwd)/${0##./})
env_script_location=$(dirname $(pwd)/${0##./})/bashrc
#echo $script_location

inst_env=0
inst_sgs=0

# check if env scripts should be installed
grep $HOME/.bashrc -e 'test -s $SCRIPTDIR/bashrc_local && . $SCRIPTDIR/bashrc_local || true' 2>&1 >/dev/null
if [ $? -ne 0 ]
then
	inst_env=1
fi

# check if SGS scripts should be installed...
grep $HOME/.bashrc -e "export PATH=\$PATH:$script_location" 2>&1 >/dev/null
if [ $? -ne 0 ]
then
	inst_sgs=1
fi

# backup ~/.bashrc
if [ $inst_env -ne 0 ] || [ $inst_sgs -ne 0 ]
then
	echo "backup $HOME/.bashrc to $HOME/.bashrc.old"
	cp $HOME/.bashrc $HOME/.bashrc.old
fi

# install env scripts
if [ $inst_env -ne 0 ]
then
	echo "Install Env scripts: update $HOME/.bashrc - include $env_script_location/bashrc_local"
	echo "" >> $HOME/.bashrc
	echo "SCRIPTDIR=$env_script_location" >> $HOME/.bashrc
	echo 'test -s $SCRIPTDIR/bashrc_local && . $SCRIPTDIR/bashrc_local || true' >> $HOME/.bashrc
else
	echo env script already installed
fi

# install SGS scripts (just add to PATH var)
if [ $inst_sgs -ne 0 ]
then
	echo "Install sgs scripts - update PATH"
	echo "" >> $HOME/.bashrc
	echo "export PATH=\$PATH:$script_location" >> $HOME/.bashrc
else
	echo sgs scripts already installed
fi
