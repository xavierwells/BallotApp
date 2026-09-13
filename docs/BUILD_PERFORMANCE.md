# Faster production rebuilds

Operator result on 2026-09-12: a warm cached build improved from approximately
15 minutes to approximately 1 minute. This is a reported result on this host,
not a cold-build guarantee or a benchmark for other machines.

These changes keep the normal production containers. There is no development
server, Compose Watch, or host-mounted frontend source tree.

## Rebuild only what changed

Run these from `D:\BallotApp` after the stack is already healthy. Each command
rebuilds and replaces just the named service; it does not restart its dependencies.

For frontend layout, text, or CSS changes:

```powershell
docker compose -f compose.yaml up -d --build --no-deps web
```

For Python application changes **without a schema migration or changed service
configuration/dependencies**:

```powershell
docker compose -f compose.yaml up -d --build --no-deps api
```

API-only changes do not need a frontend build. If both application services
changed and the prerequisites above still hold, name both: `--no-deps api web`.

For first startup, schema migrations, dependency changes, or changes to the stack
configuration, use the regular full command so Compose can run prerequisites:

```powershell
docker compose -f compose.yaml up -d --build
```

These are local-stack commands. For a deployed server, retain its production
override files and environment settings as described in [Deployment](DEPLOYMENT.md).
Do not switch an in-progress stack to a different Compose project or configuration.

## What is now cached

The web Dockerfile uses persistent BuildKit caches for:

- npm's downloaded package archives. Installs still use `npm ci`, the lockfile,
  and the existing optional-dependency exclusions. `--prefer-offline` reuses
  available downloads; it is not offline-only and does not skip integrity checks.
- Next.js compiler (SWC) downloads, which otherwise download again after a source
  change invalidates the build layer.
- Next.js incremental compilation data in `.next/cache`, which can be reused when
  rebuilding changed source files. Only this cache directory is mounted; the
  production pages and assets remain in the image.

The public API URL is set after dependency installation so changing it does not
force npm to reinstall dependencies. Tests and the production build still run
whenever their build layer is invalidated. CI audit and image-scan gates are unchanged.

The API build context now excludes local Python environments, bytecode, test
caches, and environment files. The web context also excludes TypeScript's local
incremental-build metadata. These generated files should not trigger rebuilds or
be sent to Docker as application source.

The caches belong to the Docker builder, not to the application volumes or the
Windows source directory. The first build after this change warms them. Later
builds on the same builder can reuse them; a new CI runner, a different builder,
or cache garbage collection can make a build cold again. Cache loss affects
speed, not correctness. No new packages or services are required.

Use BuildKit (the default in current Docker Desktop). Avoid routine `--no-cache`
builds or cache-pruning commands when measuring repeat-build performance. No
database reset or administrator-mode build is needed for these changes.

See Docker's [cache optimization guide](https://docs.docker.com/build/cache/optimize/),
Next.js's [build-cache guide](https://nextjs.org/docs/app/guides/ci-build-caching), and
the [npm ci documentation](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

## What the reported slow build tells us

The supplied log shows:

- The dependency-install layers were already cached.
- Next.js downloaded its compiler again; loading the configuration took about
  75 seconds.
- Compilation itself took about 7.4 minutes.
- The build's test command did not print its first output until about 110 seconds
  after the step began, although the tests themselves reported about 9 seconds.

Compiler and compilation caching address two repeatable costs. The long delay
before test output is not explained by a compiler download that occurs later.
Docker CPU/memory pressure or disk contention are possibilities, not a confirmed
diagnosis. If a second source-change build is still very slow, check Docker
Desktop's resource usage, available disk space, and whether competing builds are
running before changing application code or allocating more memory.

To compare builds without restarting the app, run:

```powershell
docker compose -f compose.yaml --progress plain build web
```

An unchanged rerun should reuse the entire build layer. The useful incremental
comparison is the next small frontend edit: the tests and build should run, but
can reuse the compiler-download and compilation caches. An unchanged `CACHED`
result alone does not demonstrate that incremental compilation is faster.

Docker execution was denied in the development assistant's shell when these
changes were made. The warm-build improvement above was subsequently confirmed
by the operator; it is not inferred from a native Windows build.
