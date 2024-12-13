#!/usr/bin/bash
#rm -rf /tmp/rpm-specs/*

#curl https://src.fedoraproject.org/lookaside/rpm-specs-latest.tar.xz > /tmp/rpm-specs-latest.tar.xz
tar axf /tmp/rpm-specs-latest.tar.xz --directory /tmp
for spec in /tmp/rpm-specs/*.spec; do
        parse.py "$spec" || echo "Error parsing $(basename $spec)" >&2
done | pv -ls $(ls /tmp/rpm-specs/*.spec | wc -l) >/dev/null
