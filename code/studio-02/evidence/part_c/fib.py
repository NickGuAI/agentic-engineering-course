def fibonacci(n):
    fib_sequence = []
    a, b = 0, 1
    for _ in range(n):
        fib_sequence.append(a)
        a, b = b, a + b
    return fib_sequence

if __name__ == "__main__":
    n = 20
    print(f"First {n} Fibonacci numbers:")
    print(fibonacci(n))
