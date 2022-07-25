import asyncio
import copy
import json
from collections import namedtuple
from typing import Optional, Iterator
import boto3
import ifcopenshell
import ifcopenshell.geom
import numpy as np
import uvicorn.middleware.wsgi
from OCC.Core import TopoDS
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from mm.vcs import Version
from utils import topo_converter, data_scheme, normal_spaces

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from fastapi.responses import StreamingResponse
import multiprocessing


class Changes(BaseModel):
    delete: Optional[list[str]]
    add: Optional[list[str]]
    modify: Optional[list[str]]


app = FastAPI(debug=True)
origins = [
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IfcIterator(Iterator):
    iterator = TopoDS.TopoDS_Iterator

    def __init__(self, compound):
        self._iterator = self.__class__.iterator()
        self._iterator.Initialize(compound)

    def __next__(self):
        if self._iterator.More():
            self._iterator.Next()
            return self._iterator.Value()

        else:
            raise StopIteration

    def more(self):
        return self._iterator.More()


class IfcValidator:
    scheme = data_scheme

    def __init__(self, schema=None, **kwargs):
        if schema is None:
            self.scheme = self.__class__.scheme
        else:
            self.scheme = schema
        self.__dict__ = kwargs

    def template(self):
        return copy.deepcopy(self.scheme)

    def __call__(self, shape, tags, color, *args, **kwargs):

        v = Version()

        # print("Validate", shape)
        try:
            #
            print(shape._fields)
            result = topo_converter(shape.geometry, *args, color=color, schema=self.template(),
                                    **kwargs)
            print("Ok")
            result["metadata"]["version"] = v.version
            result["metadata"]["tags"] = tags
            result["metadata"]["material"] = shape.styles
            return result
        except:

            print("invalid")


class DataProducer:
    def __init__(self):
        self.audits = None
        self.validator = IfcValidator(data_scheme)

    def produce(self, key, ifc_stream, num, **kwargs):
        l = key.split("/")
        l.reverse()

        settings = ifcopenshell.geom.settings(USE_PYTHON_OPENCASCADE=True)
        _data = []

        for item in ifcopenshell.geom.iterate(file_or_filename=ifc_stream, settings=settings):
            print(key, item)
            col = tuple(np.round(np.random.random(3), 2))
            __data = self.validator(item, tags=[l[1], num], color=col, **kwargs)
            if __data is not None:
                _data.append(__data)

        return _data


class BucketConsumer:
    session = boto3.session.Session()
    storage = "https://storage.yandexcloud.net/"

    def __init__(self, bucket=None):
        self.s3 = self.session.client(
            service_name='s3',
            endpoint_url=self.storage
        )

        self.bucket = bucket
        self.upd_keys_default = dict(modify=dict(), delete=[])
        self.upd_keys = dict()
        self.producer = DataProducer()

    async def __call__(self):
        """
        @event: "all" , "add", "delete", "modify".
        🇬🇧 If "all" returns the dictionary with all keys ("add", "delete", "modify").
        Otherwise, the dictionary with the selected key

        🇷🇺 Если "all" вернется словарь со всеми ключами("add", "delete", "modify")
        В противном случае словарь с выбранным ключем

        return: dict[str, list]
        🇬🇧 The function automatically sends a POST request to self.url . Failure is ignored.
        For implementations that don't involve communication via api,
        the request content is returned from the __call__ method as a dictionary.

        🇷🇺 Функция автоматически отправляет запрос POST на self.url . Неудача игнорируется.
        Для реализаций не предполагающих общение через api,
        контент запроса возвращается из методa __call__ в виде словаря.
        """
        for v in self.upd_keys.values():
            yield json.dumps(v).encode()

    def object_modify(self, state):

        for i, key in enumerate(state.modify):
            print(key)
            obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            ifc_stream = ifcopenshell.file.from_string(str(obj['Body'].read().decode()))
            self.upd_keys[key] = self.producer.produce(key=key, num=i, ifc_stream=ifc_stream)
            print(self.upd_keys[key])

    def object_add(self, state):
        print(state)
        for i, key in enumerate(state.add):
            print(key)
            obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            ifc_stream = ifcopenshell.file.from_string(obj['Body'].read().decode())

            print(ifc_stream)
            self.upd_keys[key] = self.producer.produce(key=key, num=i, ifc_stream=ifc_stream)
            print(self.upd_keys[key])

    def object_delete(self, state):

        for key in state.delete:
            del self.upd_keys[key]

    def upd_call(self, state):

        self.object_delete(state)
        self.object_add(state)
        self.object_modify(state)


namedtuple("Triplet", ["k", "val", "vers"])

consumer = BucketConsumer(bucket="lahta.contextmachine.online")


@app.post("/update")
def add_update(data: Changes):
    consumer.upd_call(data)
    # print(consumer)


@app.get("/")
async def ifcqwery():
    return StreamingResponse(consumer.__call__())


@app.get("/get_part/{key}")
async def gg(key: int):
    l = list(consumer.upd_keys.keys())[key]
    return consumer.upd_keys[l]

    # my_ren.clear()
    # my_ren.remove_temp()


@app.get("/get_keys/")
async def kk():
    return list(range(len(list(consumer.upd_keys.keys()))))


app.add_middleware(HTTPSRedirectMiddleware)

if __name__ == "__main__":
    # Popen(['python', 'file_system_observer.py'])

    uvicorn.run(
        'main:app', port=8181, host='0.0.0.0',
        ssl_keyfile="/home/sthv/ifctest/ifctest/private_key.pem",
        ssl_certfile="/home/sthv/ifctest/ifctest/certificate_full_chain.pem",

    )
