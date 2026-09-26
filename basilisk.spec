# set to nil when packaging a release, 
# or the long commit tag for the specific git branch
%define commit_tag %{nil}

# when using a commit_tag (i.e. not nil) add a commit date
# decoration ~0.yyyyMMdd to Version number
%define commit_date %{nil}

%define moz_ver 52.9.0

# palemoon's XUL version
%define pm_rel_base 20260406

# fixes error: Empty %files file …/debugsourcefiles.list
%undefine _debugsource_packages

# We should really not "provide" all the bundled libraries
%global __provides_exclude ^lib.*
# Bundled libs doesn't need to show up as a requirement either, especially
# since nothing provides them now
%global __requires_exclude ^lib(hunspell|lgpllibs|moz.*|nspr4|nss3|nssutil3|plc4|plds4|smime3|ssl3|xul)\\.so.*

Name:           basilisk
Summary:        An independent browser derived from Firefox/Mozilla community code.
Group:          Internet
License:        MPL-2.0
URL:            https://basilisk-browser.org

Version:	      2026.04.15
Release:        2
# change the source URL depending on if the package is a release version or a git version
%if "%{commit_tag}" != "%{nil}"
Source0:        https://repo.palemoon.org/Basilisk-Dev/Basilisk/archive/%{commit_tag}.tar.gz#/%{name}-%{?commit_date}.tar.gz
%else
Source0:        https://repo.palemoon.org/Basilisk-Dev/Basilisk/archive/v%version.tar.gz#/%name-%version.tar.gz
%endif

# Required for building the browser (latest release)
Source1:        https://repo.palemoon.org/MoonchildProductions/UXP/archive/RB_%{pm_rel_base}.tar.gz
Source2:        basilisk.desktop
Source3:        official.tar.xz

BuildRequires:  pkgconfig(gtk+-3.0) pkgconfig(gtk+-2.0)
BuildRequires:  pkgconfig(python2)
BuildRequires:  pkgconfig(alsa)
BuildRequires:  pkgconfig(dbus-glib-1)
BuildRequires:  pkgconfig(gconf-2.0)
BuildRequires:  pkgconfig(dri)
BuildRequires:  pkgconfig(xt)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(sqlite3)
BuildRequires:  pkgconfig(libpulse)
BuildRequires:	pkgconfig(cairo)
BuildRequires:	pkgconfig(pixman-1)
BuildRequires:	pkgconfig(libjpeg)
BuildRequires:	pkgconfig(zlib)
BuildRequires:  python2
BuildRequires:  yasm
BuildRequires:  make
BuildRequires:  zip
BuildRequires:  m4

%description
%summary

%files
%license LICENSE
%doc README.md AUTHORS
%{_bindir}/%{name}
%{_libdir}/%{name}-%{moz_ver}
%{_iconsdir}/hicolor/*x*/apps/%name.png
# FIXME this location violates the icon spec
%{_iconsdir}/hicolor/128x128/mozicon128.png
%{_datadir}/applications/%{name}.desktop

%package devel
Summary:        Development package for %name
Requires:       %name = %version
%description devel
%summary

%files devel
%{_includedir}/%{name}-%{moz_ver}
%{_libdir}/%{name}-devel-%{moz_ver}
%{_datadir}/idl/%{name}-%{moz_ver}

%prep
%autosetup -p1 -n %name
tar -xf %{S:1} --strip-components=1 -C %{_builddir}/%name/platform/
tar -xf %{S:3} -C %{_builddir}/%name/%name/branding/

# plans to merge in upstream, per Basilisk-Dev
# awaiting MR
patch -p1 < patches/0001-goanna-disable-pref.diff

# Append stuff we'd rather parse than hardcode, such
# as flags that should be autodetected but aren't
cat >%{_builddir}/%name/.mozconfig <<EOF
%ifnarch %{ix86} %{armv7} %{riscv32}
# Clear this if not a 64bit build
_BUILD_64=1
%endif

# Set GTK Version to 2 or 3
_GTK_VERSION=3

# Set Basilisk version to date timestamp
#export BASILISK_VERSION=1

# Use clang/llvm toolchain
export CC="%{__cc}"
export CXX="%{__cxx}"
export AR="%{__ar}"
export NM="%{__nm}"
export RANLIB="%{__ranlib}"
export LD="%{__ld}"

# ThinLTO with Clang/LLVM. -Wl,--undefined-version is needed due to differences between GNU ld and lld
export LDFLAGS="-flto=thin -fuse-ld=lld -Wl,--undefined-version"

# Install locations
ac_add_options --prefix=%{_prefix}
ac_add_options --libdir=%{_libdir}

# O3 for maximum optimization, -w to suppress all warnings, -flto=thin for ThinLTO
ac_add_options --enable-optimize="%{optflags} -O3 -w -flto=thin"

# Standard build options for Basilisk
ac_add_options --enable-application=basilisk
ac_add_options --enable-default-toolkit=cairo-gtk\$_GTK_VERSION
ac_add_options --enable-jemalloc
ac_add_options --enable-strip
ac_add_options --enable-devtools
ac_add_options --enable-av1
# ac_add_options --enable-jxl
ac_add_options --enable-webrtc
ac_add_options --enable-gamepad
ac_add_options --enable-pie
ac_add_options --enable-update-channel=release
ac_add_options --disable-tests
ac_add_options --disable-debug
ac_add_options --disable-necko-wifi
ac_add_options --disable-updater
ac_add_options --with-pthreads
# ac_add_options --disable-gconf
ac_add_options --enable-official-branding
ac_add_options --disable-precompiled-startupcache

export MOZILLA_OFFICIAL=1

export MOZ_PKG_SPECIAL=gtk\$_GTK_VERSION

# Use system libraries instead of bundled copies that break everything else
ac_add_options --with-system-ffi
# Seriously broken build.system...
# Error: [...]/basilisk/basilisk/installer/package-manifest.in:78: Missing file(s): bin/libhunspell.so
#ac_add_options --enable-system-hunspell
ac_add_options --enable-pulseaudio
ac_add_options --enable-system-cairo
ac_add_options --enable-system-extension-dirs
ac_add_options --enable-system-pixman
# Currently breaks: undefined symbol: BZ2_crc32Table
#ac_add_options --with-system-bz2
ac_add_options --with-system-jpeg
ac_add_options --with-system-zlib
# We should REALLY use system nspr, but the build system is too broken
#ac_add_options --with-nspr-cflags="$(pkg-config --cflags nspr)"
#ac_add_options --with-nspr-libs="$(pkg-config --libs nspr)"
EOF
./mach clobber

%build
./mach build

%install
DESTDIR=%{buildroot} ./mach install
install -m 644 -D %{S:2} %{buildroot}/%{_datadir}/applications/%name.desktop

# icons
for s in 16 32 48 256; do
	install -D -m 644 \
		%name/branding/official/default$s.png \
		%{buildroot}/%{_iconsdir}/hicolor/${s}x${s}/apps/%name.png
done

install -D -m 644 %name/branding/official/mozicon128.png \
                  %{buildroot}/%{_iconsdir}/hicolor/128x128/mozicon128.png
