from typing import Optional, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import requests
import json
from typing import Optional, Dict, Any


class APIClient:
    def __init__(self, base_url: str,timeout: int = 30, api_key: Optional[str] = None):
        """
        初始化API客户端

        :param base_url: API基础URL
        :parm timeout:
        :param api_key: 可选的API密钥
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.timeout = timeout
        # 设置默认请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'accept': 'application/json'
        })

        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

    def _make_request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None,
            timeout: int = 10
    ) -> Dict[str, Any]:
        """
        发送API请求

        :param method: HTTP方法 (GET, POST, PUT, DELETE等)
        :param endpoint: API端点
        :param params: 查询参数
        :param data: 请求体数据
        :param timeout: 请求超时时间(秒)
        :return: 解析后的JSON响应
        :raises: APIError 如果请求失败
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=timeout
            )

            # 检查响应状态码
            response.raise_for_status()
            print(1111,response.status_code)
            # 尝试解析JSON响应
            try:
                return response.json()
            except ValueError as e:
                raise APIError(f"Failed to parse JSON response: {str(e)}")

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" | Status: {e.response.status_code}"
                try:
                    error_details = e.response.json()
                    error_msg += f" | Details: {error_details}"
                except ValueError:
                    pass
            raise APIError(error_msg)

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送GET请求"""
        return self._make_request('GET', endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送POST请求"""
        return self._make_request('POST', endpoint, data=data)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送PUT请求"""
        return self._make_request('PUT', endpoint, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """发送DELETE请求"""
        return self._make_request('DELETE', endpoint)


class APIError(Exception):
    """自定义API错误异常类"""
    pass



def get_http_client(base_url: str = "", timeout: int = 300):
    httpclient = APIClient(
        base_url='http://127.0.0.1:8001/api/v1/'+ base_url,
    )
    return httpclient

def data_format(request_data,databases_obj):
    httpclient = get_http_client(base_url='')
    if databases_obj.type == '1':
        ret = httpclient.post(endpoint='omics/genome/process', data={'genome_path': request_data.file_path, 'operation': request_data.operation})
        print(ret)
    elif databases_obj.type == '5':
        ret = httpclient.post(endpoint='omics/sequence/file/process', data={'file_path': request_data.file_path})
        print(ret)
    elif databases_obj.type == '6':
        ret = httpclient.post(endpoint='omics/rnaseq/file/process', data={'file_path': request_data.file_path})
    elif databases_obj.type == '3':
        ret = httpclient.post(endpoint='omics/variants/file/process', data={'file_path': request_data.file_path})
        print(ret)