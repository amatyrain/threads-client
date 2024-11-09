import pprint
import requests


class ThreadsClient:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.base_url_v1 = 'https://graph.threads.net/v1.0'

    def _request(self, method, url, data=None, params=None, files: dict = {}):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.auth_token}',
        }

        print(f'url: {url}')
        print(f'data: {data}')
        print(f'params: {params}')
        print(f'files: {files}')

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                files=files,
            )
        except Exception as e:
            raise Exception(e)

        if response.status_code != 200:
            pprint.pprint(response.json())

        response.raise_for_status()

        return response.json()

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
        return self.publish_thread(thread['id'])

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
        endpoint = f'/me/threads'
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
        )

    def publish_thread(self, thread_id) -> dict:
        """_summary_
        example response:
            {
                'success': True
            }
        """
        endpoint = f'/me/threads_publish'
        method = 'POST'
        url = f'{self.base_url_v1}{endpoint}'

        data = {'creation_id': thread_id}

        return self._request(
            method=method,
            url=url,
            data=data,
        )

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
                    }
                ]
            }
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

    def threads_insights(
        self,
        user_id: str,
    ):
        """
        refs: https://developers.facebook.com/docs/threads/insights
        """
        endpoint = f'/{user_id}/threads_insights'
        method = 'GET'
        url = f'{self.base_url_v1}{endpoint}'

        return self._request(
            method=method,
            url=url,
            params={
                'metric': 'views,likes,replies,reposts,quotes,followers_count',
                'access_token': self.auth_token
            },
        )
