import threading
import warnings


class SingletonMeta(type):
    _instances: dict[type, object] = {}
    _lock: threading.RLock = threading.RLock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        else:
            if args or kwargs:
                warnings.warn(
                    f"{cls.__name__} 单例已初始化，传入的参数将被忽略。"
                    f"如需重新初始化，请调用 {cls.__name__}.reload_instance()",
                    stacklevel=2,
                )
        return cls._instances[cls]

    @classmethod
    def reset(mcs, cls):
        with mcs._lock:
            mcs._instances.pop(cls, None)

    @classmethod
    def reload_instance(mcs, cls):
        with mcs._lock:
            mcs._instances.pop(cls, None)
        return cls()
