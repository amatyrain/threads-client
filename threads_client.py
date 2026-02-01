import pprint
import requests
import os


class ThreadsClient:
    def __init__(self, auth_token, auto_refresh=True):
        self.auth_token = auth_token
        self.base_url_v1 = 'https://graph.threads.net/v1.0'
        self.auto_refresh = auto_refresh

        # トークンの有効性を確認し、必要に応じて初期化時にリフレッシュを試みる
        try:
            self.user_id = self.retrieve_profiles()['id']
        except Exception as e:
            error_str = str(e)
            # トークン期限切れエラーの場合、リフレッシュを試みる
            if '401' in error_str and ('expired' in error_str.lower() or 'OAuthException' in error_str):
                if self.auto_refresh:
                    print("Access token expired. Attempting to refresh...")
                    self.refresh_access_token()
                    self.user_id = self.retrieve_profiles()['id']
                else:
                    raise Exception(f"Access token expired. Please refresh manually: {e}")
            else:
                raise

    def _request(self, method, url, data=None, params=None, use_form_data=False):
        print(f'url: {url}')
        print(f'data: {data}')
        print(f'use_form_data: {use_form_data}')

        try:
            if use_form_data:
                # Threads API requires form data for certain endpoints (e.g., threads_publish)
                form_data = {**(data or {}), 'access_token': self.auth_token}
                response = requests.request(
                    method=method,
                    url=url,
                    data=form_data,
                    params=params
                )
            else:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.auth_token}',
                }
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                )
        except Exception as e:
            raise Exception(e)

        if response.status_code != 200:
            try:
                err_json = response.json()
            except Exception:
                err_json = {'error': {'message': response.text}}
            pprint.pprint(err_json)

        try:
            response.raise_for_status()
        except requests.HTTPError as he:
            # Include response body for better diagnostics
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise Exception(f"HTTPError {response.status_code} for {url}: {body}")

        return response.json()

    def refresh_access_token(self) -> dict:
        """
        Refresh the long-lived access token.
        Returns the new access token information.

        Example response:
            {
                'access_token': 'new_token_here',
                'token_type': 'bearer',
                'expires_in': 5183944  # seconds (approximately 60 days)
            }
        """
        print("Refreshing Threads access token...")
        url = 'https://graph.threads.net/refresh_access_token'

        params = {
            'grant_type': 'th_refresh_token',
            'access_token': self.auth_token
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            # 新しいトークンで更新
            self.auth_token = result['access_token']

            print(f"✅ Token refreshed successfully! Expires in {result.get('expires_in', 'unknown')} seconds")
            print(f"⚠️  IMPORTANT: Please update your secrets with the new token:")
            print(f"   New Token: {self.auth_token}")

            return result
        except requests.HTTPError as he:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise Exception(f"Failed to refresh token - HTTPError {response.status_code}: {body}")
        except Exception as e:
            raise Exception(f"Failed to refresh token: {e}")

    def retrieve_profiles(self) -> dict:
        """_summary_
        example response:
            {
                'id': 'XXXXX',
                'username': 'XXXXX',
                'threads_profile_picture_url': 'XXXXX',
                'threads_biography': 'XXXXX'
            }
        """
        endpoint = '/me'
        method = 'GET'
        url = f'{self.base_url_v1}{endpoint}'

        params = {
            'fields': 'id,username,threads_profile_picture_url,threads_biography',
            'access_token': self.auth_token
        }

        return self._request(
            method=method,
            url=url,
            params=params,
        )

    def post_thread(
        self,
        text,
        image_url = None,
    ) -> dict:
        """_summary_
        example response:
            {
                'id': '1010101010101010101'
            }
        """
        thread = self.create_thread(text, image_url)
        container_id = thread['id']

        # Poll container status until FINISHED or PUBLISHED, with a timeout
        status = self.get_container_status(container_id)
        wait_secs = 0
        max_wait = 60  # seconds
        interval = 5
        while status in ['IN_PROGRESS'] and wait_secs < max_wait:
            import time
            time.sleep(interval)
            wait_secs += interval
            status = self.get_container_status(container_id)

        if status in ['ERROR', 'EXPIRED']:
            raise Exception(f"Threads container not publishable: status={status}")

        return self.publish_thread(container_id)

    def create_thread(
        self,
        text,
        image_url = None,
    ) -> dict:
        """_summary_
        example response:
            {
                'id': '1010101010101010101'
            }
        """
        endpoint = f'/{self.user_id}/threads'
        method = 'POST'
        url = f'{self.base_url_v1}{endpoint}'

        data = {
            'text': text,
            'media_type': 'TEXT'
        }

        if image_url is not None:
            data['image_url'] = image_url
            data['media_type'] = 'IMAGE'

        return self._request(
            method=method,
            url=url,
            data=data,
            use_form_data=True,
        )

    def publish_thread(self, thread_id) -> dict:
        """_summary_
        example response:
            {
                'success': True
            }
        """
        endpoint = f'/{self.user_id}/threads_publish'
        method = 'POST'
        url = f'{self.base_url_v1}{endpoint}'

        data = {'creation_id': thread_id}

        return self._request(
            method=method,
            url=url,
            data=data,
            use_form_data=True,
        )

    def get_container_status(self, container_id: str) -> str:
        """Check publishing status for a container ID."""
        endpoint = f'/{container_id}'
        method = 'GET'
        url = f'{self.base_url_v1}{endpoint}'

        resp = self._request(
            method=method,
            url=url,
            params={'fields': 'status', 'access_token': self.auth_token},
        )
        return resp.get('status', 'UNKNOWN')

    def retrieve_thread(
        self,
        media_id,
    ) -> dict:
        """_summary_
        example response:
            {
                'data': [
                    {
                        'id': '1010101010101010101',
                        'text': 'Hello World!',
                        'likes_count': 0,
                        'replies_count': 0,
                        'retweets_count': 0,
                        'created_at': '2023-05-25T00:00:00Z'
                    },
                    {
                        'id': '2020202020202020202',
                        'text': 'Hello Threads!',
                        'likes_count': 0,
                        'replies_count': 0,
                        'retweets_count': 0,
                        'created_at': '2023-05-25T00:00:00Z'
        """
        endpoint = f'/me/threads'
        method = 'GET'
        url = f'{self.base_url_v1}{endpoint}'

        return self._request(
            method=method,
            url=url,
            params={
                'fields': 'id,text,likes_count,replies_count,retweets_count,created_at,permalink',
                'id': media_id,
                'access_token': self.auth_token
            },
        )
