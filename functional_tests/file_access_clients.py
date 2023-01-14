#!/usr/bin/env python
#from __future__ import print_function
import re
import subprocess

from abc import ABC, abstractmethod

from XRootD import client as xrd_client
from XRootD.client.flags import QueryCode


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class FileAccessClient(ABC):
    def __init__(self, url):
        self.url = url
        purl = urlparse(self.url)
        self.protocol = purl.scheme
        self.netloc = purl.netloc
        self.path = purl.path

    @property
    def server_url(self):
        return self.protocol + '://' + self.netloc

    @abstractmethod
    def read(self, chunks):
        pass

    @abstractmethod
    def readv(self, chunks):
        pass

    @abstractmethod
    def upload_file(self, local_path):
        pass

    @abstractmethod
    def download_file(self, local_path):
        pass

    @abstractmethod
    def delete_file(self):
        pass

    @abstractmethod
    def stat_file(self):
        pass

    @abstractmethod
    def get_file_checksum(self):
        pass

    def get_max_iov(self):
        pass


class GfalCMDClient(FileAccessClient):
    def upload_file(self, local_path):
        st = subprocess.run(['gfal-copy', local_path, self.url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return st.returncode, st.stdout.decode('utf-8') + '\n\n\n\n' + st.stderr.decode('utf-8')

    def delete_file(self):
        if re.match('.*/lhcb:user/lhcb/user/a/arogovsk.*', self.url):
            st = subprocess.run(['gfal-rm', self.url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            res = st.returncode, st.stdout.decode('utf-8') + '\n\n\n\n' + st.stderr.decode('utf-8')
        else:
            res = (1, 'Delete refused for safety reasons')
        return res

    def download_file(self, local_path):
        raise NotImplementedError

    def read(self, local_path):
        raise NotImplementedError

    def readv(self, local_path):
        raise NotImplementedError

    def stat_file(self, local_path):
        raise NotImplementedError

    def get_file_checksum(self, local_path):
        raise NotImplementedError



class PyXrootdClient(FileAccessClient):
    def read(self, chunks):
        res = []
        with xrd_client.File() as f:
            st, _ = f.open(self.url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for read: {1}".format(self.url, st))

            for off, sz in chunks:
                st, tres = f.read(offset=off, size=sz)
                if not st.ok:
                    raise RuntimeError("Can not read file {0} at {1},{2}: {3}".format(self.url, off, sz, st))
                res.append(tres)

        return res

    def readv(self, chunks):
        res = []
        with xrd_client.File() as f:
            st, _ = f.open(self.url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for readv: {1}".format(self.url, st))

            st, tres = f.vector_read(chunks)
            if not st.ok:
                print("Error while reading chunks {0}".format(chunks))
                raise RuntimeError("Can not readv file {0}: {1}".format(self.url, st))

        for chk in tres.chunks:
            res.append(chk.buffer)

        return res

    def upload_file(self, local_path):
        fs = xrd_client.FileSystem(self.server_url)
        st, resp = fs.copy(local_path, self.url)
        return (0 if st.ok else 1, resp)

    def download_file(self, local_path):
        raise NotImplementedError

    def delete_file(self):
        #For safety: do not delete anything except my files
        if re.match('/lhcb:user/a/arogovsk.*', self.path):
            fs = xrd_client.FileSystem(self.server_url)
            st, resp = fs.rm(self.path)
            if st.ok:
                res = (0, resp)
            else:
                res = (1, st)
        else:
            res = (1, 'Delete refused for safety reasons')
        return res

    def stat_file(self):
        with xrd_client.File() as f:
            st, _ = f.open(self.url)
            if not st.ok:
                raise RuntimeError("Can not open file {0} for stat: {1}".format(self.url, st))
            st, res = f.stat()
            if not st.ok:
                raise RuntimeError("Can not stat file {0}: {1}".format(self.url, st))
            return res

    def get_file_checksum(self):
        fs = xrd_client.FileSystem(self.server_url)
        st, resp = fs.query(xrd_client.flags.QueryCode.CHECKSUM, self.path)
        if not st.ok:
            raise RuntimeError("Can not get file {0} checksum: {1}".format(self.url, st))
        csum = None
        for cksum_data in resp.decode('ascii').split('\0'):
            ctype, csum = cksum_data.split()
            if ctype == 'adler32':
                break
        return (0, csum)

    def get_max_iov(self):
        fs = xrd_client.FileSystem(self.server_url)
        status, response = fs.query(QueryCode.CONFIG, 'readv_iov_max')
        if not status.ok:
            raise RuntimeError("Can not query server: {0}".format(status))
        return int(response.strip())

    @property
    def https_url(self):
        """
        Try to make https url from the xrootd one that we have. Useful for fallback uploads on WNs, where writing
        over xrootd is prohibited.
        """
        netloc = self.netloc
        if netloc.startswith('xrootd'):
            netloc = netloc.replace('xrootd', 'webdav', 1)

        #For https we must add port, otherwise we will end up with 443
        #If there is no port, use default one for xroot
        print("Location=|{0}|".format(netloc))
        if not re.match('^.*:[0-9]+$', netloc):
            netloc = netloc + ':1094'
        else:
           netloc = re.sub(':[0-9]+$', ':1094', netloc)

        return 'https://' + netloc + self.path


class FallbackClient:
    def __init__(self, clients, fallback_methods=None):
        self.clients = clients
        if fallback_methods is None:
            self.fallback_methods = FileAccessClient.__abstractmethods__
        else:
            self.fallback_methods = fallback_methods


    def fallback_method(self, method_name, *args, **kwargs):
        fails = []
        for cl in self.clients:
            st, resp = getattr(cl, method_name)(*args, **kwargs)
            if st != 0:
                fails.append( (st, resp) )
            else:
                return (st, resp)
        exc_text = '\n\n\n'.join("ecode: {0}\noutput: {1}".format(*x) for x in fails)
        raise RuntimeError(f"None of the clients was able to execute method {method_name}:\n{exc_text}")


    def __getattr__(self, attr):
        if attr in self.fallback_methods:
            res = lambda *args, **kwargs: self.fallback_method(attr, *args, **kwargs)
        else:
            res = getattr(self.clients[0], attr)
        return res
