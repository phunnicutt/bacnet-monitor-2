#!/bin/bash

pushd build/html
rsync -avz -e ssh * joelbender,bacmon@web.sourceforge.net:htdocs/
popd
