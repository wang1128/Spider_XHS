class Icu4cAT73 < Formula
  desc "C/C++ and Java libraries for Unicode and globalization"
  homepage "https://site.icu-project.org/home"
  url "https://github.com/unicode-org/icu/releases/download/release-73-2/icu4c-73_2-src.tgz"
  sha256 "818a80712ed3caacd9b652305e01afc7fa167e6f2e94996da44b90c2ab604ce1"
  license "GPL"

  keg_only :provided_by_macos

  def install
    args = %W[--prefix=#{prefix} --disable-samples --disable-tests --enable-static --with-library-bits=64]
    cd "source" do
      system "./configure", *args
      system "make"
      system "make", "install"
    end
  end
end
