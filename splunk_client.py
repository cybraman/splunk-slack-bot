import time
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress InsecureRequestWarning for self-signed certs (lab environment)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class SplunkClient:
    def __init__(self, base_url: str, token: str, verify_tls: bool = True, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.verify_tls = verify_tls
        self.timeout = timeout

    def _headers(self):
        return {
            "Authorization": self.token,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

    def dispatch_saved_search(self, saved_search_name: str, earliest_time: str = "-24h", latest_time: str = "now"):
        """
        Compatible method for all Splunk versions:
        Create a search job using the SPL generating command:
          | savedsearch "<saved_search_name>"
        """
        url = f"{self.base_url}/services/search/jobs"

        params = {"output_mode": "json"}
        data = {
            "search": f'| savedsearch "{saved_search_name}"',
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "exec_mode": "normal",
        }

        resp = requests.post(
            url,
            headers=self._headers(),
            params=params,
            data=data,
            verify=self.verify_tls,
            timeout=self.timeout,
        )

        # Show real Splunk error if any
        if resp.status_code >= 400:
            raise RuntimeError(f"Splunk job create failed ({resp.status_code}): {resp.text}")

        payload = resp.json()

        sid = payload.get("sid")
        if not sid and "entry" in payload and payload["entry"]:
            sid = payload["entry"][0].get("content", {}).get("sid")

        if not sid:
            raise RuntimeError(f"Could not get SID from Splunk response: {payload}")

        return sid

    def wait_for_job(self, sid: str, max_wait_sec: int = 30, poll_interval_sec: float = 1.5):
        """
        Poll job until done.
        Endpoint: /services/search/jobs/{sid}
        """
        url = f"{self.base_url}/services/search/jobs/{sid}"
        start = time.time()

        while time.time() - start < max_wait_sec:
            resp = requests.get(url, headers=self._headers(), params={"output_mode": "json"},
                                verify=self.verify_tls, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            entry = (data.get("entry") or [{}])[0]
            content = entry.get("content", {})
            is_done = content.get("isDone")

            if is_done in (True, "1", 1):
                return True

            time.sleep(poll_interval_sec)

        return False

    def get_results(self, sid: str, count: int = 5):
        """
        Fetch results once job is done.
        Endpoint: /services/search/jobs/{sid}/results
        """
        url = f"{self.base_url}/services/search/jobs/{sid}/results"
        params = {"output_mode": "json", "count": count}
        resp = requests.get(url, headers=self._headers(), params=params,
                            verify=self.verify_tls, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("results", [])

    def list_saved_searches(self, contains: str = None, limit: int = 20):
        """
        List all saved searches, optionally filtered by name.
        Endpoint: /servicesNS/-/-/saved/searches
        """
        url = f"{self.base_url}/servicesNS/-/-/saved/searches"
        params = {"output_mode": "json", "count": limit}
        resp = requests.get(url, headers=self._headers(), params=params,
                            verify=self.verify_tls, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        
        searches = []
        for entry in payload.get("entry", []):
            name = entry.get("name", "")
            content = entry.get("content", {})
            description = content.get("description", "")
            
            if contains is None or contains.lower() in name.lower():
                searches.append({
                    "name": name,
                    "description": description,
                })
        
        return searches

    def get_search_info(self, saved_search_name: str):
        """
        Get detailed info about a saved search.
        Endpoint: /servicesNS/-/-/saved/searches/{name}
        """
        url = f"{self.base_url}/servicesNS/-/-/saved/searches/{saved_search_name}"
        params = {"output_mode": "json"}
        resp = requests.get(url, headers=self._headers(), params=params,
                            verify=self.verify_tls, timeout=self.timeout)
        
        if resp.status_code >= 400:
            raise RuntimeError(f"Search not found ({resp.status_code}): {saved_search_name}")
        
        payload = resp.json()
        entry = (payload.get("entry") or [{}])[0]
        content = entry.get("content", {})
        
        return {
            "name": entry.get("name", ""),
            "description": content.get("description", ""),
            "search": content.get("search", ""),
            "owner": content.get("owner", ""),
            "app": content.get("eai:acl", {}).get("app", ""),
            "updated": content.get("updated", ""),
        }

    def run_spl_query(self, spl_query: str, earliest_time: str = "-24h", latest_time: str = "now"):
        """
        Run a raw SPL query (not a saved search).
        Endpoint: /services/search/jobs
        """
        url = f"{self.base_url}/services/search/jobs"
        params = {"output_mode": "json"}
        data = {
            "search": spl_query,
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "exec_mode": "normal",
        }
        
        resp = requests.post(
            url,
            headers=self._headers(),
            params=params,
            data=data,
            verify=self.verify_tls,
            timeout=self.timeout,
        )
        
        if resp.status_code >= 400:
            raise RuntimeError(f"Splunk query failed ({resp.status_code}): {resp.text}")
        
        payload = resp.json()
        sid = payload.get("sid")
        
        if not sid and "entry" in payload and payload["entry"]:
            sid = payload["entry"][0].get("content", {}).get("sid")
        
        if not sid:
            raise RuntimeError(f"Could not get SID from Splunk response: {payload}")
        
        return sid

    def get_server_info(self):
        """
        Get Splunk server info and version.
        Endpoint: /services/server/info
        """
        url = f"{self.base_url}/services/server/info"
        params = {"output_mode": "json"}
        resp = requests.get(url, headers=self._headers(), params=params,
                            verify=self.verify_tls, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        
        entry = (payload.get("entry") or [{}])[0]
        content = entry.get("content", {})
        
        return {
            "version": content.get("version", ""),
            "build": content.get("build", ""),
            "server_roles": content.get("server_roles", []),
        }
