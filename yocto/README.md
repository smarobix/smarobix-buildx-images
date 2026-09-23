# Yocto / meta-ros configuration

The Yocto side of this repository: the board images for the Kria K26 (KV260, KR260) and the Raspberry Pi 5, the meta-ros SDKs that `dockerfiles/oesdk` packages, and the dev containers built from the same configuration.

```
kas/                  kas files, overlaid on meta-ros's own kas configs
  smrbx-shared.yml    shared settings for every machine (caches, SDK, SSH, meta-smrbx)
  machine/            one file per Kria starter kit
  oeros-scarthgap-jazzy-k26-smk-{kv,kr}-sdt.yml   top-level configs
meta-smrbx/           local layer: OpenSSH fix, dev container image
```

These files are not standalone: the top-level configs include kas files from the `build` branch of [meta-ros](https://github.com/ros/meta-ros/tree/build/kas). The dev containers and SDK images built from them are published; the board images are not.

**Each of the unusual settings here cost a failed build. They are explained in a comment next to them; don't tidy the comments away.**

Building and flashing a board image: [Yocto boards](https://smarobix.github.io/smarobix-buildx-images/guides/yocto/) ([source](../docs/guides/yocto.md)). Rebuilding and publishing the SDKs and dev containers: [Rebuild the Yocto images](https://smarobix.github.io/smarobix-buildx-images/maintain/yocto/) ([source](../docs/maintain/yocto.md)).

Everything under `yocto/` is MIT-licensed, following the OpenEmbedded and meta-ros convention; see [`LICENSES/MIT.txt`](../LICENSES/MIT.txt).
