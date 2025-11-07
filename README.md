# ROS 2 Kria Cross-Compilation Container Registry

<!-- [![Pipeline Status](https://git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile/badges/main/pipeline.svg)](https://git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile/-/pipelines)
[![Docker Images](https://img.shields.io/badge/docker-registry-blue)](https://git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile/container_registry) -->

Pre-built ARM64 Docker containers for ROS 2 cross-compilation targeting Xilinx Kria boards and other ARM64 platforms. These images are automatically built via GitLab CI and available through GitLab Container Registry.

## 🚀 Quick Start

### Pull Pre-built Images

**Latest Stable (Jazzy):**
```bash
docker pull registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest
```

**Specific ROS 2 Distributions:**
```bash
# ROS 2 Jazzy (Ubuntu 24.04)
docker pull registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:jazzy-base
```

**Commit-specific Images:**
```bash
docker pull registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:jazzy-base-a1b2c3d
```

### Run Interactive Development Container

```bash
docker run -it --rm \
  --platform linux/arm64 \
  -v $(pwd):/workspace \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -e DISPLAY=$DISPLAY \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  bash
```

## 📋 Available Images

| Tag | ROS 2 Version | Platform | Description |
|-----|---------------|----------|-------------|
| `latest` | Jazzy | ARM64 | Latest stable build from main branch |
| `jazzy-base` | Jazzy (24.04) | ARM64 | ROS 2 Jazzy with custom OpenCV 4.5.0 |

### What's Included

- **ROS 2 Jazzy/Humble**: Full ROS 2 installation with development tools
  - **Custom OpenCV 4.10.0**: Built from source with contrib modules for features2d
  - **Xilinx Dependencies**: GStreamer plugins and drivers for Kria boards
  - **Cross-compilation Tools**: ARM64 GCC toolchain for native compilation
  - **Development Tools**: colcon, vcstool, rosdep, cmake, git, etc.

## 🔐 GitLab Container Registry Setup

### 1. Authentication

**Personal Access Token (Recommended):**
```bash
# Create token at: https://git.smarobox.de/-/user_settings/personal_access_tokens
# Scopes: read_registry, write_registry (for pushing)
export GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
echo $GITLAB_TOKEN | docker login registry.git.smarobox.de -u <your-username> --password-stdin
```

**Deploy Tokens (CI/CD):**
```bash
# Create at: Project Settings > Repository > Deploy Tokens
echo $DEPLOY_TOKEN | docker login registry.git.smarobox.de -u <deploy-username> --password-stdin
```

**GitLab CI Token (Automatic):**
```bash
# Already available in CI pipelines as $CI_REGISTRY_PASSWORD
echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
```

### 2. Configure Docker for Multi-platform

```bash
# Enable ARM64 emulation on x86_64 hosts
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify platform support
docker buildx inspect default | grep Platforms
```

## 💻 Development Workflow

### Option 1: Use Pre-built Images (Recommended)

Instead of building locally for 15+ minutes, use pre-built images:

```bash
# Pull latest image
docker pull registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest

# Run your build in container
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  --platform linux/arm64 \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  bash -c "source /opt/ros/jazzy/setup.bash && colcon build --symlink-install"
```

### Option 2: Development with Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  ros2-dev:
    image: registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest
    platform: linux/arm64
    volumes:
      - ./:/workspace
      - ros2_cache:/root/.ros
    working_dir: /workspace
    environment:
      - ROS_DOMAIN_ID=42
    stdin_open: true
    tty: true
    network_mode: host

volumes:
  ros2_cache:
```

```bash
# Start development environment
docker-compose up -d
docker-compose exec ros2-dev bash

# Inside container
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

### Option 3: Local Build (Slower)

If you need to build locally:

```bash
cd kria-ros-cross-compile/
./build_persistent.sh  # ~15 minutes first time, ~3-5 minutes subsequent
```

## 🏗️ CI/CD Pipeline

### Automatic Builds

Images are automatically built when:
- **Push to main**: Builds and tags as `latest`
- **Push to develop**: Builds development images
- **Git tags**: Creates release images
- **Manual trigger**: Via GitLab web interface

### Build Triggers

```bash
# Trigger manual build via GitLab CLI
curl -X POST \
  -F token=$CI_TRIGGER_TOKEN \
  -F ref=main \
  https://git.smarobox.de/api/v4/projects/$PROJECT_ID/trigger/pipeline
```

### Pipeline Stages

1. **Build Stage**:
   - Cross-compile ARM64 images using buildx
   - Cache optimization with registry cache
   - Multi-Dockerfile support (jazzy, humble, etc.)

2. **Tag Stage**:
   - Tag main branch builds as `latest`
   - Create commit-specific tags
   - Registry cleanup (manual)

### Cache Optimization

The pipeline uses aggressive caching:
- **Registry Cache**: Build layers cached in GitLab registry
- **Multi-stage Cache**: Optimized Dockerfile layer caching
- **Incremental Builds**: Only changed layers rebuilt

## 📦 Usage Examples

### Cross-compile ROS 2 Package

```bash
# Clone your ROS 2 workspace
git clone https://your-repo.com/ros2-workspace.git
cd ros2-workspace

# Build using pre-built container
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  --platform linux/arm64 \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  bash -c "
    source /opt/ros/jazzy/setup.bash
    rosdep install --from-paths src --ignore-src -r -y
    colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
  "
```

### Deploy to Kria Board

```bash
# Extract built artifacts
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  --platform linux/arm64 \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  tar czf kria_deploy.tar.gz install/

# Copy to Kria
rsync -avz kria_deploy.tar.gz kria-robotics:~/
ssh kria-robotics 'cd ~ && tar xzf kria_deploy.tar.gz'
```

### Run Tests in Container

```bash
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  --platform linux/arm64 \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  bash -c "
    source install/setup.bash
    colcon test
    colcon test-result --verbose
  "
```

## 🔧 Troubleshooting

### Common Issues

**Image not found:**
```bash
# Check if you're authenticated
docker login registry.git.smarobox.de

# Verify image exists
docker manifest inspect registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest
```

**Platform not supported:**
```bash
# Enable ARM64 emulation
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify qemu is loaded
ls /proc/sys/fs/binfmt_misc/ | grep qemu
```

**Build cache issues:**
```bash
# Clear local cache
docker builder prune -a

# Force rebuild without cache
docker pull registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest --no-cache
```

**Permission issues:**
```bash
# Run with same UID/GID as host
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  --user $(id -u):$(id -g) \
  registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest \
  bash
```

### Registry Debugging

```bash
# List all tags
curl -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  https://git.smarobox.de/api/v4/projects/$PROJECT_ID/registry/repositories

# Check image layers
docker manifest inspect registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:latest

# Test registry connectivity
docker pull hello-world
docker tag hello-world registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:test
docker push registry.git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile:test
```

## 🚀 Performance Comparison

| Method | First Build | Subsequent Builds | Network | Disk Space |
|--------|-------------|-------------------|---------|------------|
| Pre-built Images | ~2 minutes | ~30 seconds | High (download) | Low |
| Local Cross-compile | ~15 minutes | ~3-5 minutes | Low | High |
| Native Kria Build | ~45 minutes | ~15 minutes | None | Medium |

## 📚 Additional Resources

- [Cross-compilation Documentation](./kria-ros-cross-compile/BUILD_OPTIMIZATION.md)
- [GitLab Container Registry Docs](https://docs.gitlab.com/ee/user/packages/container_registry/)
- [Repository Link](https://git.smarobox.de/smarobix/automatica-2025/kria_ros_cross_compile)
- [Docker Buildx Multi-platform Guide](https://docs.docker.com/buildx/working-with-buildx/)
- [ROS 2 Cross-compilation Guide](https://docs.ros.org/en/jazzy/How-To-Guides/Cross-compilation.html)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Test changes with manual pipeline trigger
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Questions?** Open an issue or check the [troubleshooting section](#-troubleshooting) above.