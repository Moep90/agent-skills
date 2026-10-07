# Class wildcards and the .yml vs .yaml trap

## File extension

The omegaconf class resolver finds only `.yml` files. A class saved as `.yaml` looks
missing. When a class "does not exist" but the file is right there, check the extension.

## Class wildcards

With `--enable-class-wildcards`, a class name can glob multiple class files. Wildcards
expand before the backend sees the names, so they interact with
`ignore_class_notfound_regexp`. An exact class name that also matches a glob wins as an
exact match over the glob interpretation.

## Missing classes

`ignore_class_notfound` (and its regexp form) let a target tolerate an absent class instead
of failing the compile. Use it deliberately, not as a way to hide a typo in a class name.
When a compile reports a class not found, first confirm the dotted name maps to a real file
under `inventory/classes/`.
