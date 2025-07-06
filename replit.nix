{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.tesseract
    pkgs.poppler_utils
    pkgs.imagemagick
    pkgs.ffmpeg
    pkgs.pkg-config
    pkgs.zlib
    pkgs.moviepy
  ];
}
