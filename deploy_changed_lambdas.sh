#!/bin/bash -x

if [ "$CI" = true ]; then
    _GIT_DIFF="git diff-tree $CIRCLE_SHA1"
else
    _BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$_BRANCH" = "master" ]; then
        _GIT_DIFF="git diff-tree HEAD^"
    else
        _GIT_DIFF="git diff-tree $_BRANCH origin/master"
    fi
fi

_CHANGED_LAMBDAS=$(${_GIT_DIFF} -r --no-commit-id --name-only | grep -v "^\." | grep "/" | xargs -I{} dirname {} | sort | uniq)

for _LAMBDA in $_CHANGED_LAMBDAS
do
    echo "Deploying Lambda for ${_LAMBDA}"
    make deploy-${_LAMBDA}
done
