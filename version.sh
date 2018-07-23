#!/bin/bash

# As seen in <https://pagure.io/waiverdb/blob/master/f/rpmbuild.sh#_16>

set -ex

lasttag="$(git describe --abbrev=0 HEAD)"
lastversion="${lasttag##v}"
revbase="^$lasttag"

if [ "$(git rev-list $revbase HEAD | wc -l)" -eq 0 ] ; then
    # building a tag
    version="$lastversion"
else
    # git builds count as a pre-release of the next version
    version="$lastversion"
    version="${version%%[a-z]*}" # strip non-numeric suffixes like "rc1"
    # increment the last portion of the version
    version="${version%.*}.$((${version##*.} + 1))"
    commitcount=$(git rev-list $revbase HEAD | wc -l)
    commitsha=$(git rev-parse --short HEAD)
    version="${version}.dev${commitcount}-git.${commitsha}"
fi
echo $version
