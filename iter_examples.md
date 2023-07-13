注: 此文章不包括异步迭代器部分, 仅包含入门


# 简介
迭代器协议是可以使我们快捷的遍历一个结构的一种协议，例如我们使用`for _ in foo: pass`时，`foo`就是一个可迭代对象。  
而`for`就是用来遍历可迭代对象的一种语法糖  

# 前置知识
- 类与类方法基础知识
- 对象的概念
- 异常基础概念
- `assert`断言关键字

# 可迭代对象
在Python中，可迭代对象包含一个方法`__iter__(self)`。此方法用于获取可迭代对象的迭代器。

## 自己实现一个可迭代对象
```python
class Iterable:
    """一个可迭代对象
    迭代时返回内部`list`的迭代器
    """
    def __init__(self, data: list[int]):
        self.data = data

    def __iter__(self):
        return self.data.__iter__()


if __name__ == '__main__':
    foo = Iterable([1, 2, 3])
    iter_ = foo.__iter__()  # 获取迭代器
    assert iter_.__next__() == 1  # 获取下一个元素
    assert iter_.__next__() == 2
    assert iter_.__next__() == 3

    # 因为`list`等内置类型的构造器也是基于迭代器协议的,
    # 所以可以直接从我们写的可迭代对象构建
    assert list(foo) == [1, 2, 3]
```

# 迭代器
迭代器具有两个方法，`__iter__(self)`与`__next__(self)`。  
- `__iter__(self)`方法用于返回可迭代对象的迭代器，但是由于迭代器自身就是迭代器，所以此方法永远返回自身。
- `__next__(self)`方法用于返回每次获取的元素。如果最后一个元素已经被获取后再调用，抛出`StopIteration`异常

具有以上两种方法，且`__iter__(self)`返回自身的对象即为一个迭代器。  
因为迭代器具有`__iter__(self)`，所以迭代器也同时是一个可迭代对象。

## 自己实现一个迭代器
就拿一个由0迭代到n的迭代器举例吧
```python
class Iterator:
    """一个迭代器, 由0迭代到n(不包括n)
    """
    def __init__(self, num: int):
        self.num = num
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.i < self.num:
            # 未迭代结束
            result = self.i  # 将返回的值
            self.i += 1  # 将自身状态+1
            return result
        raise StopIteration()


if __name__ == '__main__':
    iter_ = Iterator(5)  # 一个迭代器
    # 由可迭代对象示例中得知, `list`可从可迭代对象中构建
    # 而迭代器也是一个可迭代对象
    assert list(iter_) == [0, 1, 2, 3, 4]
    try:
        iter_.__next__()
    except StopIteration:
        # 由于迭代器结束, 所以会抛出此错误, 不可继续迭代
        # 而结束原因为`list`的构建将迭代器消耗完了
        pass
    else:
        raise AssertionError()
```

# 无处不在的迭代器
## For Loop
```python
# 使用for的写法
for i in [1, 2, 3]:
    print(i)

# 实际上做的
iter_ = iter([1, 2, 3])
while True:
    try:
        i = next(iter_)  # 获取下一个元素
    except StopIteration:
        break  # 如果捕获迭代停止异常则代表迭代已结束
    
    print(i)
```

## `list`, `tuple`, `set`, `dict` 等容器的构造方法
```python
iterable = range(5)  # range是一个Iterable哦
assert list(iterable) == [0, 1, 2, 3, 4]
assert tuple(iterable) == (0, 1, 2, 3, 4)
assert set(iterable) == {0, 1, 2, 3, 4}
assert dict(zip(iterable, iterable)) == {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
```

## 迭代器解包与匹配
```python
assert [*range(5)] == [0, 1, 2, 3, 4]
a, *b, c = range(4)
assert (a, b, c) == (0, [1, 2], 3)
```

## 那些基于迭代器的方法
这里会举例一些基于迭代器协议的工具
- `zip(*args)` 用于将多个可迭代对象平行的压到一起，如果其中一个结束则整个结束
  ```python
  assert list(zip('abcdefg', range(3), range(4))) \
          == [('a', 0, 0), ('b', 1, 1), ('c', 2, 2)]
  ```
- `map(function, *args)` 将多个可迭代对象封装成一个新的迭代器，每次获取元素时获取内部每一个迭代器的下一个值并传入处理函数，然后返回处理函数返回的值。如果任意一个内部迭代器结束则整个结束，规则与`zip`相同
  ```python
  assert list(map(int.__add__, (1, 2), (3, 4, 5))) == [4, 6]
  ```
- `itertools.chain(*args)` 将多个可迭代对象连接为一个迭代器
  ```python
  import itertools
  assert list(itertools.chain((1, 2), (3, 4), (5, 6))) == [1, 2, 3, 4, 5, 6]
  ```

`itertools`是标准库中一个迭代器相关工具库，有着很多实用的工具


# 部分快捷函数
Python为很多的魔术方法都提供了用于调用其的快捷函数，如调用`__setattr__(self, name, value, /)`的`setattr(obj, name, value, /)`等。  
而`__iter__(self)`与`__next__(self)`也有对应的函数，分别为`iter(iterable)`^1^与`next(iterator[, default])`

| 函数调用     | 等价方法调用     |
| ----------- | ---------------- |
| `iter(foo)` | `foo.__iter__()` |
| `next(foo)` | `foo.__next__()` |

- `next(iterator, default)`的用法为: 当`iterator`直接结束，将返回`default`

# 生成器
有时迭代器过于麻烦，我们可以采用生成器函数来创建一个生成器。  
生成器是一个可迭代对象，会产生一个迭代器。

## Examples
```python
def foo(n: int):
    """这是一个生成器函数
    生成器函数相比手动实现可迭代对象/迭代器，可以避免复杂的中间状态保存
    一旦一个函数中含有`yield`，这个函数将被标记为生成器函数，无论这个`yield`是否能被执行到
    """
    # 首次调用`next`时会如正常函数一样，正常执行
    # 直到执行到`yield`，返回其后的值并暂停运行
    for i in range(n):
        yield i
        # 暂停后再次调用`next`会从暂停处恢复执行并重复上述操作
    # 生成器函数结束会如正常迭代器结束一样抛出`StopIteration`异常
    # 如果要获取返回值则须捕获该异常，在异常参数中获取

# 生成器函数调用后会产生一个迭代器，而不是返回值
assert list(foo(3)) == list(range(3))
```

但是有时我们还是觉得很麻烦，我们可以使用生成器推导式。语法与列表推导式一样，除了外层括号换成圆括号，行为则与生成器函数相似。

```python
assert list(i for i in range(3)) == list(range(3))
```

## 一些未介绍的
- 生成器还有向内部传值的用法，例如
  ```python
  value = yield 0
  ```
- 与生成器委托语法，将返回值任务暂时性委托给另一个可迭代对象
  ```python
  yield from [1, 2, 3]
  ```

# 文中注
1. `iter`函数还有扩展用法，此处不展开讨论

# 名词
- Iterator: 迭代器
- Iterable: 可迭代对象
- Generator: 生成器
- next: 下一个
- Callable: 可调用对象

