#!/usr/bin/env bash
# transpile.sh executes with working directory $ProjectFileDir$

set -x

pushd elm-clients/reception-kiosk

ELM=src/ReceptionKiosk.elm
JS=out/ReceptionKiosk.js
MIN=../../members/static/members/ReceptionKiosk.min.js

if elm-make --yes ${ELM} --output=${JS} && minify ${JS} > ${MIN}
then
    sed -i "1i// Generated by Elm" ${JS}
    sed -i "1i// Generated by Elm" ${MIN}
fi

paplay /usr/share/sounds/ubuntu/stereo/dialog-information.ogg
popd

