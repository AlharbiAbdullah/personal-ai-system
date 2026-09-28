# Sync Architecture (optional)

Most users run this vault on **one machine** and can ignore this file. It documents an
**optional** pattern for keeping the same vault in sync across two or more machines. If you
run a single machine, nothing here applies.

## The problem

The vault is a git repo. If you edit it on two machines, naive `git pull/push` from both
sides produces merge conflicts, especially on binary or derived state (the ChromaDB index,
session state). You want exactly one machine to be the source of truth.

## The pattern: single coordinator

Pick **one machine as the sole coordinator**. Only the coordinator:
- writes to the git remote (`origin`),
- rebuilds the ChromaDB semantic index,
- runs the scheduled maintenance job.

Every other machine is a **passive replica** that receives changes from the coordinator
(over SSH on a private network, for example) and never pushes to `origin` itself.

```
  ┌─────────────────┐        push/pull         ┌──────────┐
  │   COORDINATOR    │ ───────────────────────▶ │  origin  │  (GitHub)
  │  (one machine)   │                          └──────────┘
  │  - sole origin   │
  │    writer        │        SSH (private net)
  │  - builds index  │ ───────────────────────▶ ┌─────────────────┐
  │  - runs cron     │                          │     REPLICA      │
  └─────────────────┘                           │  (other machines)│
                                                │  read-only sync  │
                                                └─────────────────┘
```

## Wiring it (placeholders, fill in your own)

| Role | Host | User | Private IP |
|------|------|------|------------|
| Coordinator | `<coordinator-host>` | `<user>` | `<coordinator-private-ip>` |
| Replica | `<replica-host>` | `<user>` | `<replica-private-ip>` |

1. Put both machines on a private mesh network (a mesh VPN works well) so
   the coordinator can reach the replica over SSH without exposing anything publicly.
2. On the **coordinator**, schedule a maintenance job (cron, systemd timer, or launchd) that:
   commits local changes, pulls and merges, rebuilds the index, pushes to `origin`, then
   pushes the updated tree to each replica over SSH.
3. On a **replica**, the wake or refresh step is pull-only: fetch from the coordinator, never
   push to `origin`.

The reference maintenance scripts live in `03-rai/skills/rai/scheduled/`. Adapt the host
names, users, and IPs to your setup, or delete them if you run a single machine.

## Rules that keep it from breaking

- **One origin writer.** Only the coordinator pushes to GitHub. Replicas that push cause
  divergence.
- **Don't sync derived state.** The ChromaDB index is rebuilt from source memory. Let each
  machine (or just the coordinator) regenerate it rather than syncing the binary store.
  It is gitignored for this reason, and it starts empty on a fresh clone.
- **Fast-forward only on the replica.** A replica that has diverged should reset to the
  coordinator's tree, not merge.
