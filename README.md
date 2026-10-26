# 图像重建工具箱

(working in progress)

## 怎么用

`uv run imgproc`

---

## 怎么安装 COLMAP

安装 COLMAP 的编译时依赖，以Fedora系统为例:

```sh
sudo dnf install -y \
    git \
    cmake \
    ninja-build \
    gcc-c++ \
    boost-devel \
    eigen3-devel \
    OpenImageIO-devel \
    OpenImageIO-utils \
    metis-devel \
    glog-devel \
    gtest-devel \
    gmock-devel \
    sqlite-devel \
    glew-devel \
    qt6-qtbase-devel \
    qt6-qtsvg-devel \
    CGAL-devel \
    ceres-solver-devel \
    suitesparse-devel \
    suitesparse-static \
    libcurl-devel \
    openssl-devel \
    openblas-devel
```

_具体参考 <https://colmap.github.io/install.html#build-from-source>_

克隆 COLMAP 仓库:

```sh
# 在任何合适的目录
git clone https://github.com/colmap/colmap.git
cd colmap
```

执行 cmake:

```sh
# colmap/
mkdir build
cd build
# colmap/build/
cmake .. -GNinja
```

用 ninja 构建，要耗费一些时间:

```sh
# colmap/build/
ninja
```

获取 colmap 的绝对路径:

```sh
# colmap/build/
readlink -f src/colmap/exe/colmap
# 输出类似 /home/sbchild/colmap/build/src/colmap/exe/colmap
```

写到本项目的 `tools.toml` (不存在则创建):

```toml
[colmap]
bin = "/home/sbchild/colmap/build/src/colmap/exe/colmap"
```

## 主要依赖

- COLMAP: <https://github.com/colmap/colmap>
- RAW图像处理库: <https://github.com/letmaik/rawpy>
- tiff解析器: <https://github.com/cgohlke/tifffile>

## 注意事项

- [LibRaw](https://github.com/LibRaw/LibRaw) 没法处理擦掉 EXIF 信息的 ORF 图像，预期会爆炸。
