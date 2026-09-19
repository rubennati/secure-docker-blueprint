#!/bin/sh
set -e

# None of these images reads a secret from a file. For every NAME__FILE variable
# set in the service, read the file it points to into NAME, then hand off to the
# command that follows. The __FILE variables hold paths, not values.
for _v in $(env | sed -n 's/^\([A-Za-z0-9_]*\)__FILE=.*/\1/p'); do
  eval "_f=\${${_v}__FILE}"
  # shellcheck disable=SC2154 # _f is set by the eval above
  _val="$(cat "$_f")"
  export "$_v=$_val"
done
unset _v _f _val

exec "$@"
