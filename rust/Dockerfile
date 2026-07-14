# Dockerfile for cross-compiling pwnghost for ARM architectures
# Build: docker buildx build --platform linux/arm64,linux/arm/v7,linux/arm/v6 -t pwnghost:latest --push -f rust/Dockerfile .
# 
# This uses amd64 rust image as builder and cross-compiles for all ARM targets

# ============================================================================
# Base builder stage (amd64 rust image with cross-compilation toolchains)
# ============================================================================
FROM --platform=linux/amd64 rust:1.85 AS builder

WORKDIR /build

# Install cross-compilation dependencies
# Install cross-compilation dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-aarch64-linux-gnu \
    gcc-arm-linux-gnueabihf \
    libc6-dev-arm64-cross \
    libc6-dev-armhf-cross \
    pkg-config \
    libudev-dev \
    libasound2-dev \
    libdbus-1-dev \
    libpcap-dev \
    && dpkg --add-architecture arm64 && dpkg --add-architecture armhf \
    && apt-get update && apt-get install -y --no-install-recommends \
    libdbus-1-dev:arm64 \
    libdbus-1-dev:armhf \
    libpcap-dev:arm64 \
    libpcap-dev:armhf \
    && rm -rf /var/lib/apt/lists/*

# Add Rust targets
RUN rustup target add \
    aarch64-unknown-linux-gnu \
    armv7-unknown-linux-gnueabihf \
    arm-unknown-linux-gnueabihf

# Configure cargo for cross-compilation
RUN mkdir -p /root/.cargo && printf '%s\n' \
    '[target.aarch64-unknown-linux-gnu]' \
    'linker = "aarch64-linux-gnu-gcc"' \
    '' \
    '[target.armv7-unknown-linux-gnueabihf]' \
    'linker = "arm-linux-gnueabihf-gcc"' \
    '' \
    '[target.arm-unknown-linux-gnueabihf]' \
    'linker = "arm-linux-gnueabihf-gcc"' \
    '' \
    '[build]' \
    'rustflags = ["-C", "link-arg=-Wl,--as-needed"]' \
    > /root/.cargo/config.toml

# Allow cross-compilation without pkg-config sysroot
ENV PKG_CONFIG_ALLOW_CROSS=1
ENV CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
ENV CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc
ENV CARGO_TARGET_ARM_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc

# Copy Cargo files first for caching
COPY rust/Cargo.toml rust/Cargo.lock ./

# Create dummy source to cache dependencies
RUN mkdir -p src && echo 'fn main() {}' > src/main.rs && cargo build --release 2>/dev/null || true

# Copy actual source
COPY rust/src ./src
COPY rust/faces ./faces

# Build all three targets
RUN PKG_CONFIG_SYSROOT_DIR=/usr/aarch64-linux-gnu PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig cargo build --release --target aarch64-unknown-linux-gnu --features with-dbus
RUN PKG_CONFIG_SYSROOT_DIR=/usr/arm-linux-gnueabihf PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabihf/pkgconfig cargo build --release --target armv7-unknown-linux-gnueabihf --features with-dbus
RUN PKG_CONFIG_SYSROOT_DIR=/usr/arm-linux-gnueabihf PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabihf/pkgconfig cargo build --release --target arm-unknown-linux-gnueabihf --features with-dbus

# ============================================================================
# Runtime stage - minimal Debian with runtime deps
# ============================================================================
FROM debian:bookworm-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libasound2 \
    libudev1 \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# Create pwnghost user
RUN useradd -r -s /bin/false -U pwnghost

# Copy binaries from builder
COPY --from=builder /build/target/aarch64-unknown-linux-gnu/release/pwnghost /usr/local/bin/pwnghost-aarch64
COPY --from=builder /build/target/armv7-unknown-linux-gnueabihf/release/pwnghost /usr/local/bin/pwnghost-armv7
COPY --from=builder /build/target/arm-unknown-linux-gnueabihf/release/pwnghost /usr/local/bin/pwnghost-armv6

# Auto-detect architecture and execute appropriate binary
RUN printf '%s\n' '#!/bin/bash' \
    'ARCH=$(uname -m)' \
    'case "$ARCH" in' \
    '    aarch64|arm64) exec /usr/local/bin/pwnghost-aarch64 "$@" ;;' \
    '    armv7l|armv7)  exec /usr/local/bin/pwnghost-armv7 "$@" ;;' \
    '    armv6l|armv6)  exec /usr/local/bin/pwnghost-armv6 "$@" ;;' \
    '    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;' \
    'esac' \
    > /usr/local/bin/pwnghost
RUN chmod +x /usr/local/bin/pwnghost

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD pgrep -x pwnghost > /dev/null || exit 1

ENTRYPOINT ["pwnghost"]