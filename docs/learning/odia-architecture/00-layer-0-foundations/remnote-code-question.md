```python
class_names = ["person", "cup"]

result = get_classes()
print(result)
```

- Which function correctly completes this program? >>A)
  ```python
  def get_classes():
      # Return the original list to the caller.
      return class_names

  # result becomes ["person", "cup"], so print(result)
  # displays the original class list.
  ```
  ```python
  def get_classes():
      print(class_names)
  ```
  ```python
  def get_classes():
      return "class_names"
  ```
  ```python
  def get_classes():
      return None
  ```
