# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: MIT

# Interactive SSH to the KV260 died after ~18 s with "Broken pipe", while
# commands without a terminal worked. When a PTY is allocated, OpenSSH switches
# its packets to an "interactive" DSCP/QoS marking, and the board's marked
# replies are lost between the board and the LAN: a debug sshd showed the
# command running and exiting 0 while the client never received it. Setting
# IPQoS none on the client does not help; on the server it does.
do_install:append() {
    printf '\n# Board-originated packets with interactive DSCP marking are lost\n# on the path to the LAN; see meta-smrbx openssh_%%.bbappend.\nIPQoS none\n' \
        >> ${D}${sysconfdir}/ssh/sshd_config
}
