// This is a simple wrapper to enable React Suspense for data fetching.
// It creates a resource that can be read by a component, which will
// either return the data, throw a promise (triggering Suspense), or throw an error.

type Status = 'pending' | 'success' | 'error';

function wrapPromise<T>(promise: Promise<T>) {
  let status: Status = 'pending';
  let result: T;
  let error: any;

  const suspender = promise.then(
    (r: T) => {
      status = 'success';
      result = r;
    },
    (e: any) => {
      status = 'error';
      error = e;
    },
  );

  return {
    read(): T {
      if (status === 'pending') {
        throw suspender; // This is what triggers Suspense
      } else if (status === 'error') {
        throw error; // This will be caught by an Error Boundary
      } else if (status === 'success') {
        return result;
      }
      // Should be unreachable
      throw new Error('Awaited promise is in an unknown state');
    },
  };
}

// In a real app, you would have a more robust cache
const cache = new Map<string, any>();

export function fetchData<T>(key: string, promiseFn: () => Promise<T>) {
  if (!cache.has(key)) {
    cache.set(key, wrapPromise(promiseFn()));
  }
  return cache.get(key)!;
}
