%define git_repo python-openerp-libclient

#define distsuffix xrg

%{?!py_requires: %global py_requires(d) BuildRequires: python}
%{?!py_sitedir: %global py_sitedir %(python -c 'import distutils.sysconfig; print distutils.sysconfig.get_python_lib()' 2>/dev/null || echo PYTHON-LIBDIR-NOT-FOUND)}

Name:		python-openerp-libclient
Summary:	Client Library for the OpenERP protocol
Version:	%git_get_ver
Release:	%mkrel %git_get_rel
URL:		http://git.hellug.gr/?p=xrg/openerp-libcli
Source0:	%git_bs_source %{name}-%{version}.tar.gz
License:	LGPLv3
BuildArch:	noarch
Group:		Libraries
BuildRequires:	python
%py_requires -d

%description
This library allows client applications connect and work 
against an OpenERP server

%prep
%git_get_source
%setup -q

%build
python setup.py build
# TODO docs

%install
python setup.py install --root=%{buildroot} --compile
# --optimize=2

%files
%defattr(-,root,root)
%doc README
%{py_sitedir}/*

