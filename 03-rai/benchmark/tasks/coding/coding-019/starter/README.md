# Release diff

Before a release is promoted we compare the staged tree with the live tree to see exactly which
files were added, removed or changed. `sample/old` and `sample/new` are two small trees to try it
on. The tool must be plain bash plus coreutils, because it runs on minimal hosts.
