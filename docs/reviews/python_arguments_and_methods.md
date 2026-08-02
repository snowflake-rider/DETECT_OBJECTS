# Python 인자와 메서드 기초

`CameraFinder` 코드를 보면서 헷갈렸던 Python 문법을 복습하기 위한
문서입니다.

## 1. 위치 인자와 키워드 인자

다음과 같은 함수가 있다고 가정합니다.

```python
def connect(host, port):
    print(host, port)
```

### 위치 인자

값의 위치를 기준으로 전달합니다.

```python
connect("localhost", 8080)
```

- 첫 번째 값은 `host`
- 두 번째 값은 `port`

순서를 잘못 전달하면 의도하지 않은 값이 들어갈 수 있습니다.

### 키워드 인자

인자 이름을 직접 적어서 전달합니다.

```python
connect(host="localhost", port=8080)
```

이름을 명시하기 때문에 각 값의 의미를 쉽게 알 수 있습니다. 순서를 바꿔도
괜찮습니다.

```python
connect(port=8080, host="localhost")
```

## 2. 함수 인자 사이의 `*`

함수 선언에서 단독으로 사용하는 `*`는 그 뒤에 나오는 인자를
키워드 인자로만 받겠다는 의미입니다.

```python
def connect(host, *, port=8080):
    print(host, port)
```

다음 호출은 가능합니다.

```python
connect("localhost", port=3000)
```

하지만 `port`를 위치 인자로 전달하면 오류가 발생합니다.

```python
connect("localhost", 3000)
# TypeError
```

`*`를 제거하면 모든 인자를 위치 또는 키워드 방식으로 전달할 수 있습니다.

```python
def connect(host, port=8080):
    print(host, port)


connect("localhost", 3000)
connect(host="localhost", port=3000)
```

현재 `CameraFinder` 생성자도 `*`가 없으므로 다음 두 방식이 모두
가능합니다.

```python
finder = CameraFinder(0, 9, 5, 0.1, "auto")
```

```python
finder = CameraFinder(
    start_index=0,
    max_index=9,
    attempts=5,
    retry_delay=0.1,
    backend="auto",
)
```

인자가 많을 때는 각 값의 의미가 잘 보이는 키워드 방식을 사용하는 것이
좋습니다.

## 3. 일반 메서드

먼저 클래스를 **붕어빵 틀**, 객체를 **그 틀로 만든 붕어빵 한 개**라고
생각해 봅시다.

```python
class FishBread:
    def __init__(self, flavor):
        self.flavor = flavor

    def introduce(self):
        print(f"나는 {self.flavor} 붕어빵입니다.")
```

```python
red_bean = FishBread("팥")
cream = FishBread("크림")

red_bean.introduce()  # 나는 팥 붕어빵입니다.
cream.introduce()  # 나는 크림 붕어빵입니다.
```

`red_bean.introduce()`를 호출할 때 `self`는 `red_bean`입니다.
`cream.introduce()`를 호출할 때 `self`는 `cream`입니다.

즉, `self`는 **지금 이 메서드를 실행하고 있는 붕어빵 한 개**입니다.
각 붕어빵의 맛처럼 객체마다 다른 값을 사용하려면 일반 메서드가
필요합니다.

Python은 다음 두 코드를 거의 같은 의미로 처리합니다.

```python
red_bean.introduce()
FishBread.introduce(red_bean)
```

`CameraFinder.scan()`과 `_probe()`는 생성자에 저장된 인덱스 범위,
재시도 횟수 등을 사용합니다. `finder` 객체마다 설정이 다를 수 있으므로
일반 메서드입니다.

## 4. `@staticmethod`

이번에는 붕어빵 이름이 올바른지 확인하는 기능을 만들어 봅시다.

```python
class FishBread:
    @staticmethod
    def is_valid_flavor(flavor):
        return flavor in ("팥", "크림", "피자")
```

```python
FishBread.is_valid_flavor("팥")  # True
FishBread.is_valid_flavor("딸기")  # False
```

이 함수는 특정 붕어빵의 `self.flavor`를 읽지 않습니다. 붕어빵 틀에
저장된 값도 읽지 않습니다. 전달받은 `flavor`만 검사합니다.

따라서 `self`와 `cls`가 모두 필요 없습니다.

> `staticmethod`는 클래스 안에 정리해 둔 독립적인 도구 함수입니다.

`CameraFinder.get_raspberry_pi_model()`은 파일에서 Raspberry Pi 모델을
읽습니다. 특정 finder의 `start_index` 같은 값을 사용하지 않고
`CameraFinder` 클래스의 속성도 사용하지 않습니다. 그래서
`staticmethod`입니다.

```python
model = CameraFinder.get_raspberry_pi_model()
```

## 5. `@classmethod`

`classmethod`의 `cls`는 붕어빵 한 개가 아니라 **붕어빵 틀 자체**입니다.

메뉴 번호만 받아 새로운 붕어빵을 만드는 기능을 생각해 봅시다.

```python
class FishBread:
    def __init__(self, flavor):
        self.flavor = flavor

    @classmethod
    def from_menu(cls, menu_number):
        menu = {
            1: "팥",
            2: "크림",
            3: "피자",
        }
        return cls(menu[menu_number])
```

```python
bread = FishBread.from_menu(2)
print(bread.flavor)  # 크림
```

`FishBread.from_menu(2)`를 호출하면 Python이 `FishBread` 클래스를
`cls`로 자동 전달합니다.

```python
return cls(menu[menu_number])
```

위 코드는 이번 예제에서 다음과 같습니다.

```python
return FishBread("크림")
```

즉, `classmethod`는 다음 상황에서 자주 사용합니다.

- 클래스에 저장된 공통값을 읽거나 변경할 때
- 여러 가지 방식으로 객체를 만들어 주는 보조 생성자가 필요할 때
- 상속한 자식 클래스도 같은 생성 기능을 사용하게 만들 때

`CameraFinder.get_environment()`에서는 `cls`로 같은 클래스의
`get_raspberry_pi_model()`을 호출합니다.

```python
@classmethod
def get_environment(cls):
    pi_model = cls.get_raspberry_pi_model()
```

```python
CameraFinder.get_environment()
# cls는 CameraFinder
```

사실 현재처럼 간단한 코드에서는 `get_environment()`도
`staticmethod`로 만들 수 있습니다. `classmethod`를 사용한 이유는 나중에
자식 클래스가 `get_raspberry_pi_model()`을 바꾸더라도 `cls`를 통해
바뀐 메서드를 호출할 수 있게 하기 위해서입니다.

## 6. 차이 한눈에 보기

| 종류 | 붕어빵 비유 | 자동으로 받는 값 |
|---|---|---|
| 일반 메서드 | 만들어진 붕어빵 한 개를 사용 | `self` = 그 객체 |
| `classmethod` | 붕어빵 틀 자체를 사용 | `cls` = 그 클래스 |
| `staticmethod` | 옆에 놓인 독립적인 도구 | 없음 |

기억하기 쉽게 줄이면 다음과 같습니다.

- `self`: 이 객체
- `cls`: 이 클래스
- `staticmethod`: 둘 다 필요 없음

## 7. 어떤 메서드를 선택할까?

다음 순서로 생각하면 쉽습니다.

### 질문 1: `self.start_index`처럼 객체에 저장된 값이 필요한가?

필요하면 일반 메서드입니다.

```python
def scan(self):
    print(self.start_index)
```

### 질문 2: 객체 값은 필요 없지만 클래스 자체가 필요한가?

필요하면 `classmethod`입니다.

```python
@classmethod
def create_default(cls):
    return cls(start_index=0)
```

### 질문 3: 객체도 클래스도 필요 없는가?

그렇다면 `staticmethod` 또는 클래스 밖의 일반 함수로 만들 수 있습니다.

```python
@staticmethod
def is_valid_index(index):
    return index >= 0
```

한 줄로 정리하면 다음과 같습니다.

```text
객체 값 필요   → 일반 메서드(self)
클래스 필요    → classmethod(cls)
둘 다 불필요   → staticmethod
```

## 8. 짧은 확인 문제

다음 기능에 어울리는 메서드는 무엇일까요?

1. 현재 finder의 `start_index`부터 카메라를 검색한다.
2. 전달받은 숫자가 0 이상인지 확인한다.
3. 기본 설정으로 새로운 `CameraFinder` 객체를 만든다.

정답:

1. 객체의 설정을 사용하므로 일반 메서드
2. 객체와 클래스가 필요 없으므로 `staticmethod`
3. `cls(...)`로 객체를 만들 수 있으므로 `classmethod`
