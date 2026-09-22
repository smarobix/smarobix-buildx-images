# CI and releases

## The workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `build-images.yml` | pull request, push to `main`, `v*` tag, manual | Builds the images, pushes them to GHCR, and on a `v*` tag packages the `.deb` and `.tar.gz` files and publishes a GitHub Release |
| `docs.yml` | push to `main`, release, manual | Builds the documentation site and deploys it to GitHub Pages |
| `reuse.yml` | pull request, push to `main` | Runs `reuse lint`: every file needs copyright and licence information, and every licence named needs its text under `LICENSES/` |
| `dockerhub-mirror.yml` | manual only | Copies one published tag to the Docker Hub mirror |

Dependabot opens a pull request per base-image digest weekly, per Dockerfile directory, and bumps the pinned actions monthly.

## What each event builds

| Event | Images built | Pushed to GHCR | `.deb` and release |
|---|---|---|---|
| Pull request | Only those whose inputs changed | No | No |
| Push to `main` | All | Yes, as `:<id>` | No |
| `v*` tag | All | Yes, the same `:<id>` tags | Yes |
| Manual run | All | Yes | No |

A manual run pushes the same rolling tags as a branch build, so start one from `main`.

There is no second branch. Rolling tags come from `main` only, and there are no versioned image tags: a `v*` tag rebuilds everything and re-pushes the same rolling tags, then creates the release. A tag such as `k26-jazzy` therefore always moves. Anyone who needs a reproducible build should pin the digest, which `docker buildx imagetools inspect` prints.

The `:<id>-buildcache` tags in the registry are BuildKit cache, not images.

## Pull request scope

A pull request builds only the images whose inputs it changes. An image's inputs are its `dockerfiles/<dir>/` directory; `build-images.yml`, `targets.yml` and `tools/targets.py` count as inputs for all of them, so a change to any of those builds everything. An image that is skipped still reports success, so it never blocks a merge.

A pull request never logs in to the registry and pushes nothing, and a pull request from a fork gets a read-only token in any case. A green pull request build means the Dockerfiles still compile.

Two things a pull request does **not** tell you:

- **The `package` job never runs.** `compute-depends.sh`, the control fields and the install message are exercised for the first time during a release. Check them by hand: [`.deb` dependencies](deb-dependencies.md#check-a-change-before-it-ships).
- **Pull requests do not write the registry cache.** After a base image moves, every pull request rebuilds that image cold until a push to `main` exports a fresh cache. One green `main` build repairs the whole matrix; the next build of the same image is a cache hit in about a minute.

Pull requests from forks run on the self-hosted runners, so read a fork's diff before approving its workflow run.

## Runners

The jobs run on self-hosted runners, selected per target by `build.runs_on` in `targets.yml`.

- **`arm64` targets build on the native arm64 runner** (`[self-hosted, ARM64]`). Emulated `arm64` is not an option: `qemu-aarch64` silently loses files from the colcon merge-install prefix partway through a large source build, which surfaces later as a package failing to find an already-installed library such as `rcutils`.
- **`armv7` targets build under emulation on the x86_64 hosts** (`[self-hosted, X64]`). armv7 emulation does not have that problem.
- **The `package` job matches the build job's runner**, because the `.deb` is assembled by running the image.

The build job has `timeout-minutes: 240`. A hung emulated build otherwise holds a runner for GitHub's six-hour default, and that has happened. A cold armv7 source build takes around two and a half hours, so the cap leaves room for a real build while cutting a hang much sooner.

The image push and the cache export run in parallel, and `cache-to` carries `ignore-error=true`: a rejected cache-layer upload once cancelled a finished image push, which left the tag on an older build while the job merely looked failed. A missing cache costs the next build some time; a missing image is a failed release.

After a build that matters, check what was published rather than the job result:

```bash
docker buildx imagetools inspect ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy \
  --format '{{json .Image}}'
```

`created` and the `org.opencontainers.image.revision` label should match the commit you expect.

## Cut a release

A release publishes the `.deb` and `.tar.gz` install trees. The images themselves are already on GHCR from `main`.

1. Make sure the last `main` build is green and the images are the ones you want to package.
2. Tag `main` and push the tag. The current release is `v1.1.0`, so the next one is `v1.2.0` or `v1.1.1`:

   ```bash
   git switch main && git pull
   git tag -a v1.2.0 -m "v1.2.0"
   git push origin v1.2.0
   ```

3. The workflow builds every image, then runs one `package` job per target that has a `deb` entry, and finally one `release` job that collects every `pkg-*` artifact and attaches them all to a single GitHub Release with generated notes.

**Use a plain `vMAJOR.MINOR.PATCH` tag.** The tag becomes the package version verbatim, minus the `v`: `v1.2.0` gives `1.2.0` in the `Version:` control field and in every filename, `smarobix-ros-<distro>-<pkg>_1.2.0_<arch>.deb`. A suffix such as `-rc.1` does not mean what it looks like: dpkg reads everything after a hyphen as the Debian revision, so `1.2.0-rc.1` sorts *above* `1.2.0`, and a release candidate would win an upgrade against the final release.

If a `package` job fails, the `release` job does not run. The tag is already pushed, so re-run the failed jobs rather than re-tagging:

```bash
gh run rerun <run-id> --failed
```

The download links on the documentation site are pinned to the newest `v*` tag, so check afterwards that the site has rebuilt against the new release.

## SDK releases

The Yocto SDK installers are bitbake output, too large to commit and not reproducible in CI, so they are published as assets of their own release, which the `oe-sdk` build then downloads and verifies by checksum. See [Rebuild the Yocto images](yocto.md) for producing them.

The tag is `yocto-sdk-<distro>-<date>`, as in `yocto-sdk-jazzy-2026.09.15`. Two rules matter:

- **Publish with "Set as latest" off.** These releases share one release stream with the `v*` releases. If an SDK release becomes "latest", every `releases/latest/download/...` link to a `.deb` starts returning 404. The documentation pins its links to a tag for the same reason.

  ```bash
  gh release create yocto-sdk-jazzy-2026.09.15 --latest=false \
    --title "meta-ros Yocto SDKs, Jazzy (2026-09-15)" \
    --notes-file notes.md \
    oecore-*.sh
  ```

  Afterwards, `gh release list` must still show a `v*` release as Latest.
- **Never name the tag `v…`.** A `v*` tag triggers the whole build, package and release pipeline.

Do not replace the assets of an existing SDK release either. The installer's sha256 is pinned in `targets.yml`, and older commits would stop building. A new SDK gets a new release, and then the `oe-sdk` entries in `targets.yml` are updated to its tag, filenames and checksums:

```bash
sha256sum oecore-ros2-image-sdktest-jazzy-aarch64-cortexa72-cortexa53-k26-smk-kv-sdt-toolchain-nodistro.0.sh
```

That change touches `targets.yml`, so the pull request builds every image; the `oe-sdk` jobs download the new installer, check the sha256 and build on the published dev container.

## The Docker Hub mirror

`dockerhub-mirror.yml` copies one published tag to Docker Hub with `docker buildx imagetools create`, which moves the manifest without pulling the layers. It is manual, it does nothing on its own, and a mirrored tag does not follow later rebuilds.

```bash
gh workflow run dockerhub-mirror.yml -f tag=k26-jazzy
```

It needs the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets and fails at the Docker Hub login without them. The default target repository is a personal namespace, which is why user documentation does not point at it; the mirror is to move to an organisation namespace.

## The hand-pushed Yocto dev containers

The `yocto-native` dev containers, `k26-yocto-jazzy` and `rpi5-yocto-jazzy`, are bitbake output. CI does not build them, and it should not: a job that reached into a build host's Yocto downloads and sstate would not be reproducible anywhere else. Their entries in `targets.yml` carry `build: null` and `published: manual`, so `tools/targets.py` leaves them out of the build matrix and the generated table marks them as pushed by hand.

They are still real inputs to CI. `dockerfiles/oesdk` builds `FROM` the dev container tag, so after pushing a new one, start a build on `main` to rebuild the SDK images on top of it:

```bash
gh workflow run build-images.yml --ref main
```

[Rebuild the Yocto images](yocto.md#publish-the-dev-container) has the build and push steps.
