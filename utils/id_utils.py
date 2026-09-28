from typing import Iterator

def id_generator(start: int=1) -> Iterator[str]:
    i = start
    while True:
        yield str(i)
        i += 1
