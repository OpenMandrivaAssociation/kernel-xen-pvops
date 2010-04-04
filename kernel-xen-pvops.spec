%define name                    kernel-xen-pvops
%define version                 2.6.32.11
%define rel                     1
%define kernel_version          2.6.32.11
%define kernel_extraversion     xen-pvops-%{rel}mdv
# ensures file uniqueness
%define kernel_file_string      %{kernel_version}-%{kernel_extraversion}
# ensures package uniqueness
%define kernel_package_string   %{kernel_version}-%{rel}mdv
%define kernel_source_dir       %{_prefix}/src/%{name}-%{kernel_package_string}
%define kernel_devel_dir        %{_prefix}/src/%{name}-devel-%{kernel_package_string}

%define _default_patch_fuzz 3

%ifarch %ix86
%define config %{SOURCE1}
%endif
%ifarch x86_64
%define config %{SOURCE2}
%endif

Name:       %{name}
Version:    %{version}
Release:    %mkrel %{rel}
Summary:    The Xen PV-OPS kernel
Group:      System/Kernel and hardware
License:    GPL
Source0:    linux-%{kernel_version}.tar.bz2
Source1:    i386_defconfig-server
Source2:    x86_64_defconfig-server
Source12:   disable-mrproper-in-devel-rpms.patch
Source13:   kbuild-really-dont-remove-bounds-asm-offsets-headers.patch
BuildRoot:  %{_tmppath}/%{name}-%{version}

%description 
The XEN PVOPS kernel.

%package %{kernel_package_string}
Version:    1
Release:    %mkrel 1
Summary:    XEN kernel
Group:      System/Kernel and hardware
Provides:   kernel = %{kernel_version}
Provides:   kernel-xen = %{kernel_version}
Requires(post):	bootloader-utils mkinitrd xen-hypervisor
Requires(postun):	bootloader-utils

%description %{kernel_package_string}
The XEN PVOPS kernel.

%package devel-%{kernel_package_string}
Version:    1
Release:    %mkrel 1
Summary:    XEN kernel devel files
Group:      System/Kernel and hardware
Provides:   kernel-devel = %{kernel_version}
Autoreqprov: no

%description devel-%{kernel_package_string}
This package contains the kernel-devel files that should be enough to build 
3rdparty drivers against for use with the %{kname}-%{buildrel}.

%package source-%{kernel_package_string}
Version:    1
Release:    %mkrel 1
Summary:    XEN kernel sources
Group:      System/Kernel and hardware
Provides:   kernel-source = %{kernel_version}
Autoreqprov: no

%description source-%{kernel_package_string}
This package contains the source code files for the Linux 
kernel. Theese source files are only needed if you want to build your own 
custom kernel that is better tuned to your particular hardware.

%package debug-%{kernel_package_string}
Version:  1
Release:  %mkrel 1
Summary:  Xen kernel debug files
Group:    Development/Debug
Requires: glibc-devel
Provides: kernel-debug = %{kernel_version}
Autoreqprov: no

%description debug-%{kernel_package_string}
This package contains the kernel-debug files that should be enough to 
use debugging/monitoring tool (like systemtap, oprofile, ...)

%package doc-%{kernel_package_string}
Version:    1
Release:    %mkrel 1
Summary:    XEN kernel documentation
Group:      System/Kernel and hardware
Autoreqprov: no

%description doc-%{kernel_package_string}
This package contains documentation files form the kernel source. Various
bits of information about the Linux kernel and the device drivers shipped
with it are documented in these files. You also might want install this
package if you need a reference to the options that can be passed to Linux
kernel modules at load time.

%prep
%setup -q -n linux-%{kernel_version}
%apply_patches

%build
perl -p \
    -e 's/CONFIG_LOCALVERSION=.*/CONFIG_LOCALVERSION="-%{kernel_extraversion}"/' \
    < %config > .config
%make oldconfig
%make
%make modules

%install
rm -rf %{buildroot}
install -d -m 755 %{buildroot}/boot
install -m 644 System.map %{buildroot}/boot/System.map-%{kernel_file_string}
install -m 644 .config %{buildroot}/boot/config-%{kernel_file_string}
install -m 644 arch/x86/boot/bzImage \
    %{buildroot}/boot/vmlinuz-%{kernel_file_string}

# modules
%make modules_install INSTALL_MOD_PATH=%{buildroot}

# remove firmwares
rm -rf %{buildroot}/lib/firmware

# remove symlinks
rm -f %{buildroot}/lib/modules/%{kernel_file_string}/build
rm -f %{buildroot}/lib/modules/%{kernel_file_string}/source

# strip modules, as spec-helper won't recognize them once compressed
find %{buildroot}/lib/modules/%{kernel_file_string}/kernel -name *.ko \
    -exec objcopy --only-keep-debug '{}' '{}'.debug \;
find %{buildroot}/lib/modules/%{kernel_file_string}/kernel -name *.ko \
    -exec objcopy --add-gnu-debuglink='{}'.debug --strip-debug '{}' \;
find %{buildroot}/lib/modules/%{kernel_file_string}/kernel -name *.ko.debug | \
    sed -e 's|%{buildroot}||' > kernel_debug_files.list

# create an exclusion list for those debug files
sed -e 's|^|%exclude |' < kernel_debug_files.list > no_kernel_debug_files.list

# compress modules
find %{buildroot}/lib/modules/%{kernel_file_string} -name *.ko | xargs gzip -9
/sbin/depmod -u -ae -b %{buildroot} -r \
    -F %{buildroot}/boot/System.map-%{kernel_file_string} \
    %{kernel_file_string}

# create modules description
pushd %{buildroot}/lib/modules/%{kernel_file_string}
find . -name *.ko.gz | xargs /sbin/modinfo | \
    perl -lne 'print "$name\t$1" if $name && /^description:\s*(.*)/; $name = $1 if m!^filename:\s*(.*)\.k?o!; $name =~ s!.*/!!' \
    > modules.description
popd

# install kernel sources
install -d -m 755 %{buildroot}%{kernel_source_dir}
tar cf - . \
    --exclude '*.o' --exclude '*.ko'  --exclude '*.cmd' \
    --exclude '.temp*' --exclude '.tmp*' \
    --exclude modules.order --exclude .gitignore \
    | tar xf - -C %{buildroot}%{kernel_source_dir}
chmod -R a+rX %{buildroot}%{kernel_source_dir}

# we remove all the source files that we don't ship
# first architecture files
for i in alpha arm arm26 avr32 blackfin cris frv h8300 ia64 microblaze mips \
    m32r m68k m68knommu mn10300 parisc powerpc ppc s390 sh sh64 sparc v850 xtensa; do
    rm -rf %{buildroot}%{kernel_source_dir}/arch/$i
    rm -rf %{buildroot}%{kernel_source_dir}/include/asm-$i
done

%ifnarch %{ix86} x86_64
    rm -rf %{buildroot}%{kernel_source_dir}/arch/x86
    rm -rf %{buildroot}%{kernel_source_dir}/include/asm-x86
%endif

rm -rf %{buildroot}%{kernel_source_dir}/vmlinux
rm -rf %{buildroot}%{kernel_source_dir}/System.map
rm -rf %{buildroot}%{kernel_source_dir}/Module.*
rm -rf %{buildroot}%{kernel_source_dir}/*.list
rm -rf %{buildroot}%{kernel_source_dir}/.config.*
rm -rf %{buildroot}%{kernel_source_dir}/.missing-syscalls.d
rm -rf %{buildroot}%{kernel_source_dir}/.version
rm -rf %{buildroot}%{kernel_source_dir}/.mailmap

# install devel files 
install -d -m 755 %{buildroot}%{kernel_devel_dir}
for i in $(find . -name 'Makefile*'); do
    cp -R --parents $i %{buildroot}%{kernel_devel_dir};
done
for i in $(find . -name 'Kconfig*' -o -name 'Kbuild*'); do
    cp -R --parents $i %{buildroot}%{kernel_devel_dir};
done
cp -fR include %{buildroot}%{kernel_devel_dir}
cp -fR scripts %{buildroot}%{kernel_devel_dir}
%ifarch %{ix86} x86_64
    cp -fR arch/x86/kernel/asm-offsets.{c,s} \
        %{buildroot}%{kernel_devel_dir}/arch/x86/kernel/
    cp -fR arch/x86/kernel/asm-offsets_{32,64}.c \
        %{buildroot}%{kernel_devel_dir}/arch/x86/kernel/
    cp -fR arch/x86/include %{buildroot}%{kernel_devel_dir}/arch/x86/
%else
    cp -fR arch/%{target_arch}/kernel/asm-offsets.{c,s} \
        %{buildroot}%{kernel_devel_dir}/arch/%{target_arch}/kernel/
    cp -fR arch/%{target_arch}/include \
        %{buildroot}%{kernel_devel_dir}/arch/%{target_arch}/
%endif
cp -fR .config Module.symvers %{buildroot}%{kernel_devel_dir}

# Needed for truecrypt build (Danny)
cp -fR drivers/md/dm.h %{buildroot}%{kernel_devel_dir}/drivers/md/

# Needed for external dvb tree (#41418)
cp -fR drivers/media/dvb/dvb-core/*.h \
    %{buildroot}%{kernel_devel_dir}/drivers/media/dvb/dvb-core/
cp -fR drivers/media/dvb/frontends/lgdt330x.h \
    %{buildroot}%{kernel_devel_dir}/drivers/media/dvb/frontends/

# add acpica header files, needed for fglrx build
cp -fR drivers/acpi/acpica/*.h \
    %{buildroot}%{kernel_devel_dir}/drivers/acpi/acpica/

# disable mrproper
patch -p1 -d %{buildroot}%{kernel_devel_dir} -i %{SOURCE12}

# disable bounds.h and asm-offsets.h removal
patch -p1 -d %{buildroot}%{kernel_devel_dir} -i %{SOURCE13}

%post %{kernel_package_string}
/sbin/installkernel %{kernel_file_string}
pushd /boot > /dev/null
if [ -L vmlinuz-xen ]; then
        rm -f vmlinuz-xen
fi
ln -sf vmlinuz-%{kernel_file_string} vmlinuz-xen
if [ -L initrd-xen.img ]; then
        rm -f initrd-xen.img
fi
ln -sf initrd-%{kernel_file_string}.img initrd-xen.img
popd > /dev/null

%postun %{kernel_package_string}
/sbin/installkernel -R %{kernel_file_string}
pushd /boot > /dev/null
if [ -L vmlinuz-xen ]; then
        if [ "$(readlink vmlinuz-xen)" = "vmlinuz-%{kernel_file_string}" ]; then
                rm -f vmlinuz-xen
        fi
fi
if [ -L initrd-xen.img ]; then
        if [ "$(readlink initrd-xen.img)" = "initrd-%{kernel_file_string}.img" ]; then
                rm -f initrd-xen.img
        fi
fi
popd > /dev/null

%post devel-%{kernel_package_string}
if [ -d /lib/modules/%{kernel_file_string} ]; then
    ln -sf %{kernel_devel_dir} /lib/modules/%{kernel_file_string}/build
    ln -sf %{kernel_devel_dir} /lib/modules/%{kernel_file_string}/source
fi

%preun devel-%{kernel_package_string}
if [ -L /lib/modules/%{kernel_file_string}/build ]; then
    rm -f /lib/modules/%{kernel_devel_string}/build
fi
if [ -L /lib/modules/%{kernel_file_string}/source ]; then
    rm -f /lib/modules/%{kernel_devel_string}/source
fi

%post source-%{kernel_package_string}
if [ -d /lib/modules/%{kernel_file_string} ]; then
    ln -sf %{kernel_source_dir} /lib/modules/%{kernel_file_string}/build
    ln -sf %{kernel_source_dir} /lib/modules/%{kernel_file_string}/source
fi

%preun source-%{kernel_package_string}
if [ -L /lib/modules/%{kernel_file_string}/build ]; then
    rm -f /lib/modules/%{kernel_source_string}/build
fi
if [ -L /lib/modules/%{kernel_file_string}/source ]; then
    rm -f /lib/modules/%{kernel_source_string}/source
fi

%clean
rm -rf %{buildroot}

%files %{kernel_package_string} -f no_kernel_debug_files.list
%defattr(-,root,root)
/lib/modules/%{kernel_file_string}
/boot/System.map-%{kernel_file_string}
/boot/config-%{kernel_file_string}
/boot/vmlinuz-%{kernel_file_string}

%files devel-%{kernel_package_string}
%defattr(-,root,root)
%{kernel_devel_dir}

%files source-%{kernel_package_string}
%defattr(-,root,root)
%{kernel_source_dir}
%exclude %{kernel_source_dir}/Documentation

%files doc-%{kernel_package_string}
%defattr(-,root,root)
%{kernel_source_dir}/Documentation

%files debug-%{kernel_package_string} -f kernel_debug_files.list
%defattr(-,root,root)
