#!/bin/bash

[[ -z "$1" || -z "$2" ]] && {
	echo >&2 "Usage: $0 <firefox package.exe> <file_prefix>"
	echo >&2 "Example: $0 ~/Downloads/Firefox_Setup_21.0.exe 21"
	echo >&2
	echo >&2 'Script uses "7z" to unpack and objdump to extract ordinal names.'
	echo >&2 'Stuff gets unpacked to tmp dir in cwd that should be cleaned-up afterwards.'
	echo >&2 'Symbols names will be stored to a "<file_prefix>.<lib>.txt" file.'
	echo >&2
	echo >&2 'Get any version of Firefox packages via links like these (i.e. for 21.0):'
	echo >&2 '  http://download.mozilla.org/?product=firefox-21.0&os=win&lang=en-US'
	echo >&2 '  http://download-installer.cdn.mozilla.net/pub/mozilla.org/firefox/releases/21.0/win32/en-US/Firefox%20Setup%2021.0.exe'
	exit 1
}

tmpdir=$(mktemp -d unpack.XXXXXX)

src=$(readlink -f "$1")
pushd "$tmpdir" >/dev/null
7z x "$src" >/dev/null || exit
popd >/dev/null

for lib in "$tmpdir"/core/*.dll; do
	dst=${lib##*/}
	dst="$2"."${dst%.dll}".txt
	objdump -x "$lib" |
		sed -n '/Ordinal\/Name Pointer/,/^$/p' |
		awk '!/^[[:space:]]*$/ && $NF!="Table" {print $NF}' |
		sort -u >"$dst"
	echo "Created: $dst"
done

rm -rf "$tmpdir"
exit 0
