// SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
// SPDX-License-Identifier: Apache-2.0

// Target picker on the home page. It reads targets.json, which
// tools/build-site.sh generates from targets.yml for the current release, so
// every image tag, file name and URL it prints exists. Nothing about a target
// is written here; only the wording per family is.
//
// Targets that share a "board" label form one entry in the board list. An
// oe-sdk target is offered as the alternative to the yocto-native target of
// the same board and distro, not as a choice of its own.

(() => {
  "use strict";

  const ROOT_ID = "buildx-picker";
  const DEFAULT_RMW = "rmw_cyclonedds_cpp";
  const ARCH_LABELS = {
    arm64: "64-bit (arm64)",
    armhf: "32-bit (armhf)",
    amd64: "64-bit x86 (amd64)",
  };

  // --- HTML building. Every value from targets.json passes through esc(). ---

  class Html {
    constructor(text) {
      this.text = text;
    }
    toString() {
      return this.text;
    }
  }

  const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (value) => String(value).replace(/[&<>"']/g, (c) => ESCAPES[c]);

  const part = (value) => {
    if (value === null || value === undefined || value === false) return "";
    if (Array.isArray(value)) return value.map(part).join("");
    return value instanceof Html ? value.text : esc(value);
  };

  const html = (strings, ...values) =>
    new Html(strings.reduce((out, s, i) => out + s + (i < values.length ? part(values[i]) : ""), ""));

  // --- Labels. ---

  const capitalise = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const archLabel = (arch) => ARCH_LABELS[arch] || arch;
  const osKey = (t) => `${t.os.name}|${t.os.codename}`;

  // "Debian 13" plus the codename "trixie" reads better as "Debian 13
  // (trixie)", but a name that already carries the codename, or a bracket of
  // its own, is left alone.
  function osLabel(os) {
    const name = os.name || "";
    const codename = os.codename || "";
    if (!name) return codename;
    if (!codename || name.includes("(") || name.toLowerCase().includes(codename.toLowerCase())) return name;
    return `${name} (${codename})`;
  }

  // --- Data model. ---

  function isTarget(t) {
    return t && typeof t === "object" && ["id", "board", "distro", "family"].every((k) => typeof t[k] === "string");
  }

  // True when one distro comes in more than one value of key within the
  // group, so the reader has to choose it. When the value follows from the
  // distro, as Ubuntu's release does on the K26, there is nothing to ask.
  function varies(targets, key) {
    const seen = new Map();
    return targets.some((t) => {
      const values = seen.get(t.distro) || new Set();
      values.add(key(t));
      seen.set(t.distro, values);
      return values.size > 1;
    });
  }

  function groupTargets(targets) {
    const groups = new Map();
    for (const t of targets) {
      t.os = t.os || {};
      if (!groups.has(t.board)) groups.set(t.board, { label: t.board, main: [], sdk: [] });
      const group = groups.get(t.board);
      (t.family === "oe-sdk" ? group.sdk : group.main).push(t);
    }
    for (const group of groups.values()) {
      // A board with only an SDK image still gets an entry of its own.
      if (!group.main.length) [group.main, group.sdk] = [group.sdk, []];
      group.pickOs = varies(group.main, osKey);
      group.pickArch = varies(group.main, (t) => t.arch);
    }
    return [...groups.values()];
  }

  // --- Output, per family. ---

  function snippet(code, label) {
    return html`<div class="buildx-picker__snippet"><pre><code>${code}</code></pre><button type="button" class="buildx-picker__copy" aria-label="Copy ${label}">Copy</button></div>`;
  }

  function step(title, note, ...rest) {
    return html`<section class="buildx-picker__step"><h3>${title}</h3>${note ? html`<p>${note}</p>` : ""}${rest}</section>`;
  }

  function buildxConf(ctx, t) {
    const lines = ["method = docker", `docker_image = ${ctx.registry}:${t.id}`];
    if (t.platform) lines.push(`docker_platform = ${t.platform}`);
    return lines.join("\n");
  }

  const CONF_NOTE = html`Put this in <code>.buildx.conf</code> at the root of your workspace, the directory that holds <code>src/</code>, then run <code>colcon buildx</code>.`;

  function qemuNote(ctx) {
    return html` On an x86_64 computer, register QEMU once first; see <a href="${ctx.page("how-to/build-on-x86_64/")}">Build on an x86_64 host</a>.`;
  }

  function crossBuild(ctx, t) {
    return step("2 · Cross-build your workspace", html`On your computer, not on the board. ${CONF_NOTE}${t.platform ? qemuNote(ctx) : ""}`, snippet(buildxConf(ctx, t), "the .buildx.conf"));
  }

  function ubuntuApt(ctx, t) {
    const d = t.distro;
    const rmw = t.rmw || DEFAULT_RMW;
    const guide = `https://docs.ros.org/en/${d}/Installation/Ubuntu-Install-Debs.html`;
    const commands = [
      `sudo apt install ros-${d}-ros-base ros-${d}-${rmw.replace(/_/g, "-")}`,
      `source /opt/ros/${d}/setup.bash`,
      `export RMW_IMPLEMENTATION=${rmw}`,
    ];
    return [
      step(
        "1 · ROS 2 on the board",
        html`The board runs ${osLabel(t.os)}, so use the official ROS 2 apt packages. Nothing from this project goes on the board. Add packages.ros.org as the <a href="${guide}">ROS 2 ${capitalise(d)} install guide</a> describes, then, on the board:`,
        snippet(commands.join("\n"), "the commands for the board"),
      ),
      crossBuild(ctx, t),
    ];
  }

  // pynq and debian: our .deb from the GitHub release.
  function debPackage(ctx, t) {
    const d = t.distro;
    const rmw = t.rmw || DEFAULT_RMW;
    if (!t.deb || !t.deb.filename) {
      return [
        step("1 · ROS 2 on the board", html`No <code>.deb</code> is published for this target. See the <a href="${ctx.reference}">targets reference</a>.`),
        crossBuild(ctx, t),
      ];
    }
    const file = t.deb.filename;
    const arch = t.deb.arch || t.arch;
    const check = t.os.codename
      ? html`<code>grep CODENAME /etc/os-release</code> should show <strong>${t.os.codename}</strong>, and <code>dpkg --print-architecture</code> should print <strong>${arch}</strong>`
      : html`<code>dpkg --print-architecture</code> should print <strong>${arch}</strong>`;
    const commands = [
      `wget ${ctx.releaseBase}${file}`,
      `sudo apt install ./${file}`,
      `source /opt/ros/${d}/setup.bash`,
      `export RMW_IMPLEMENTATION=${rmw}`,
    ];
    return [
      step(
        "1 · ROS 2 on the board",
        html`The package is built for ${osLabel(t.os)} on ${archLabel(arch)}. Check the board first: ${check}. Then, on the board:`,
        snippet(commands.join("\n"), "the commands for the board"),
      ),
      crossBuild(ctx, t),
    ];
  }

  function sdkImage(ctx, sdk, heading) {
    const image = `${ctx.registry}:${sdk.id}`;
    return html`<h4>${heading}</h4><p>The SDK image cross-compiles on your computer, so it needs no <code>docker_platform</code>. ${CONF_NOTE}</p>${snippet(buildxConf(ctx, sdk), "the .buildx.conf for the SDK image")}<p>Its tag has only an arm64 entry. On an x86_64 computer, pull it once with the platform first, or the build fails with "no matching manifest":</p>${snippet(`docker pull --platform linux/arm64 ${image}`, "the docker pull command")}`;
  }

  // yocto-native, with the oe-sdk image of the same board and distro if any.
  function yocto(ctx, native, sdk) {
    const d = (native || sdk).distro;
    const onBoard = step(
      "1 · ROS 2 on the board",
      html`ROS 2 comes with the board image (<code>ros-image-core</code>), which you build from <code>yocto/</code> in smarobix-buildx-images; board images are not published. The <a href="${ctx.page("tutorials/meta-ros/")}">meta-ros tutorial</a> walks through it. The image has no bash, so source <code>setup.sh</code>:`,
      snippet(`. /opt/ros/${d}/setup.sh`, "the command for the board"),
    );
    if (!native) {
      return [onBoard, step("2 · Cross-build your workspace", "", sdkImage(ctx, sdk, "The SDK image"))];
    }
    return [
      onBoard,
      step(
        "2 · Cross-build your workspace",
        html`Recommended: the dev container, which builds natively and also generates the Python message bindings. ${CONF_NOTE}${qemuNote(ctx)}`,
        snippet(buildxConf(ctx, native), "the .buildx.conf for the dev container"),
        sdk ? sdkImage(ctx, sdk, "…or the SDK image") : "",
      ),
    ];
  }

  // A family this script doesn't know yet: the image is still usable.
  function otherFamily(ctx, t) {
    return [
      step("1 · ROS 2 on the board", html`See the <a href="${ctx.reference}">targets reference</a> for this board.`),
      crossBuild(ctx, t),
    ];
  }

  function render(ctx, t, sdk) {
    switch (t.family) {
      case "ubuntu-apt":
        return ubuntuApt(ctx, t);
      case "pynq":
      case "debian":
        return debPackage(ctx, t);
      case "yocto-native":
        return yocto(ctx, t, sdk);
      case "oe-sdk":
        return yocto(ctx, null, t);
      default:
        return otherFamily(ctx, t);
    }
  }

  // --- Controls. ---

  // Replace a select's options, keeping the current choice when it is still
  // offered. Unchanged lists are left alone so a screen reader isn't told
  // about a change that didn't happen.
  function fill(select, options) {
    const signature = JSON.stringify(options);
    if (select.dataset.options === signature) return;
    const previous = select.value;
    select.replaceChildren(...options.map(([value, label]) => new Option(label, value)));
    select.dataset.options = signature;
    if (options.some(([value]) => value === previous)) select.value = previous;
  }

  const unique = (list) => [...new Map(list.map((item) => [item[0], item])).values()];

  function field(name, label) {
    return html`<div class="buildx-picker__field" data-field="${name}"><label for="buildx-picker-${name}">${label}</label><select id="buildx-picker-${name}" data-select="${name}"></select></div>`;
  }

  function build(root, data, ctx) {
    const targets = Array.isArray(data && data.targets) ? data.targets.filter(isTarget) : [];
    if (!targets.length || typeof data.registry !== "string") throw new Error("targets.json lists no targets");
    const groups = groupTargets(targets);
    const release = data.release_tag || (data.version ? `v${data.version}` : "");
    ctx.registry = data.registry;
    ctx.releaseBase = String(data.release_base_url || "").replace(/\/?$/, "/");

    root.innerHTML = String(html`
      <div class="buildx-picker__bar"><strong>Commands for your board</strong><span>${release ? `release ${release} · ` : ""}${data.registry} · <a href="${ctx.reference}">all targets</a></span></div>
      <div class="buildx-picker__pick">
        ${field("board", "Board")}${field("os", "OS on the board")}${field("arch", "OS architecture")}${field("distro", "ROS 2 distro")}
      </div>
      <div class="buildx-picker__out"></div>
      <p class="buildx-picker__sr" aria-live="polite"></p>`);

    const select = (name) => root.querySelector(`[data-select="${name}"]`);
    const out = root.querySelector(".buildx-picker__out");
    const status = root.querySelector("[aria-live]");

    fill(select("board"), groups.map((g, i) => [String(i), g.label]));

    const update = () => {
      const group = groups[Number(select("board").value)];
      let pool = group.main;

      root.querySelector('[data-field="os"]').hidden = !group.pickOs;
      if (group.pickOs) {
        fill(select("os"), unique(pool.map((t) => [osKey(t), osLabel(t.os)])));
        pool = pool.filter((t) => osKey(t) === select("os").value);
      }
      root.querySelector('[data-field="arch"]').hidden = !group.pickArch;
      if (group.pickArch) {
        fill(select("arch"), unique(pool.map((t) => [t.arch, archLabel(t.arch)])));
        pool = pool.filter((t) => t.arch === select("arch").value);
      }
      fill(select("distro"), unique(pool.map((t) => [t.distro, capitalise(t.distro)])));

      const target = pool.find((t) => t.distro === select("distro").value);
      const sdk = group.sdk.find((t) => t.distro === target.distro) || null;
      out.innerHTML = String(html`${render(ctx, target, sdk)}`);
    };

    root.addEventListener("change", (event) => {
      if (event.target.matches("select")) update();
    });
    out.addEventListener("click", (event) => {
      const button = event.target.closest(".buildx-picker__copy");
      if (button) copy(button, status);
    });
    update();
  }

  // --- Copy buttons. ---

  function copy(button, status) {
    const code = button.parentElement.querySelector("code");
    const done = (message) => {
      button.textContent = message;
      status.textContent = "";
      window.setTimeout(() => {
        status.textContent = message;
      }, 50);
      window.clearTimeout(button.resetTimer);
      button.resetTimer = window.setTimeout(() => {
        button.textContent = "Copy";
      }, 2000);
    };
    // Without clipboard access (plain http, or permission denied) select the
    // text, so a keyboard copy takes it.
    const fallback = () => {
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      let copied = false;
      try {
        copied = document.execCommand("copy");
      } catch (err) {
        copied = false;
      }
      done(copied ? "Copied" : "Selected, copy with the keyboard");
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(code.textContent).then(() => done("Copied"), fallback);
    } else {
      fallback();
    }
  }

  // --- Start-up. ---

  function fail(root, ctx, error) {
    root.innerHTML = String(html`
      <div class="admonition warning" role="status">
        <p class="admonition-title">The target picker could not load</p>
        <p>It reads <code>targets.json</code>, which the site build generates, and that failed (${error.message || error}). Every target, image tag and <code>.deb</code> file is also listed in the <a href="${ctx.reference}">targets reference</a>.</p>
      </div>`);
  }

  function init() {
    const root = document.getElementById(ROOT_ID);
    if (!root || root.dataset.ready) return;
    root.dataset.ready = "true";

    // targets.json sits at the site root; data-targets gives its path relative
    // to this page, which holds under the /smarobix-buildx-images/ prefix.
    const source = new URL(root.dataset.targets || "targets.json", document.baseURI);
    const siteRoot = new URL(".", source);
    // The static text in index.md links the targets reference, and MkDocs has
    // already turned that link into the right URL for this page.
    const link = root.querySelector("a[href]");
    const ctx = {
      page: (path) => new URL(path, siteRoot).href,
      reference: link ? link.href : new URL("reference/targets/", siteRoot).href,
    };

    fetch(source, { cache: "no-cache" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => build(root, data, ctx))
      .catch((error) => {
        console.error("buildx picker:", error);
        fail(root, ctx, error);
      });
  }

  // Material re-runs page scripts through document$ when instant navigation
  // is on; without it document$ still fires once for the first page.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
