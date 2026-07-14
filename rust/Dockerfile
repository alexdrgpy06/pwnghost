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
    && dpkg --add-architecture arm64 \
    && apt-get update && apt-get install -y --no-install-recommends \
    libdbus-1-dev:arm64 \
    libpcap-dev:arm64 \
    && rm -rf /var/lib/apt/lists/*

# Add Rust targets
RUN rustup target add aarch64-unknown-linux-gnu

# Configure cargo for cross-compilation
RUN mkdir -p /root/.cargo && printf '%s\n' \
    '[target.aarch64-unknown-linux-gnu]' \
    'linker = "aarch64-linux-gnu-gcc"' \
    '[build]' \
    'rustflags = ["-C", "link-arg=-Wl,--as-needed"]' \
    > /root/.cargo/config.toml

# Allow cross-compilation without pkg-config sysroot
ENV PKG_CONFIG_ALLOW_CROSS=1
ENV CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc

# Copy Cargo files first for caching
COPY Cargo.toml ./
    
# Create dummy source to cache dependencies
RUN mkdir -p src && echo 'fn main() {}' > src/main.rs && cargo build --release 2>/dev/null || true
    
# Copy actual source
COPY src ./src
COPY faces ./faces

# Build aarch64
RUN PKG_CONFIG_SYSROOT_DIR=/usr/aarch64-linux-gnu PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig cargo build --release --target aarch64-unknown-linux-gnu --features with-dbus

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

# Copy binary from builder
COPY --from=builder /build/target/aarch64-unknown-linux-gnu/release/pwnghost /usr/local/bin/pwnghost

RUN chmod +x /usr/local/bin/pwnghost

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD pgrep -x pwnghost > /dev/null || exit 1

ENTRYPOINT ["pwnghost"]