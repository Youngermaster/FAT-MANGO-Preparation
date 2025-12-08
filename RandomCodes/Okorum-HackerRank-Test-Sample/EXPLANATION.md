# Understanding the Search Application - Beginner's Guide

## What Does This Code Do?

This is a **search application** that counts how many times a search term appears. It's like searching on Google and getting "About 1,234 results found" - but simplified for learning!

---

## The Three Main Files

### 1. **mock-api.js** - The Fake Database

Think of this as a pretend internet service that gives you search results.

```javascript
const countMatches = (searchTerm) => {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const value = Math.floor(Math.random() * 100) + 1;
      if (searchTerm !== "error") {
        resolve(value);
      } else {
        reject(new Error("CONNECTION_ERROR"));
      }
    }, 100);
  });
};
```

**What's happening here?**

- **Promise**: A promise is like ordering pizza - you get a promise that the pizza will arrive, but you have to wait!
- **setTimeout**: Waits 100 milliseconds (0.1 seconds) to simulate internet delay
- **Math.random()**: Creates a random number between 1-100 (pretend search results)
- **resolve(value)**: "Success! Here are your results!"
- **reject(error)**: "Oops! Something went wrong!" (happens if you search for "error")

---

### 2. **search.js** - The Smart Search Engine

This file uses something special called **EventEmitter**. Think of it like a radio station:

- The radio station (EventEmitter) broadcasts different shows (events)
- Listeners tune in to specific shows they care about

```javascript
const API = require("./mock-api");
const EventEmitter = require("events");

class Search extends EventEmitter {
  searchCount(searchTerm) {
    // Step 1: Check if search term is valid
    if (searchTerm === undefined) {
      this.emit("SEARCH_ERROR", {
        message: "INVALID_TERM",
      });
      return;
    }

    // Step 2: Tell everyone "I'm starting to search!"
    this.emit("SEARCH_STARTED", searchTerm);

    // Step 3: Ask the API for results
    API.countMatches(searchTerm)
      .then((count) => {
        // Step 4: Got results! Tell everyone!
        this.emit("SEARCH_SUCCESS", {
          count: count,
          term: searchTerm,
        });
      })
      .catch((error) => {
        // Step 5: Something went wrong! Tell everyone!
        this.emit("SEARCH_ERROR", {
          message: error.message,
          term: searchTerm,
        });
      });
  }
}
```

**Breaking it down:**

#### Step 1: Validation

```javascript
if (searchTerm === undefined) {
  this.emit("SEARCH_ERROR", { message: "INVALID_TERM" });
  return;
}
```

- Like checking if someone actually typed something in the search box
- If empty, broadcast "ERROR!" and stop

#### Step 2: Announce Start

```javascript
this.emit("SEARCH_STARTED", searchTerm);
```

- Broadcasts: "Hey everyone! I'm searching for: [searchTerm]"

#### Step 3-5: Get Results

```javascript
API.countMatches(searchTerm)
  .then((count) => {
    /* Success! */
  })
  .catch((error) => {
    /* Failed! */
  });
```

- **then**: What to do when the promise succeeds
- **catch**: What to do when the promise fails

---

### 3. **index.js** - Putting It All Together

This is where everything comes alive! It's like setting up listeners for a radio show.

```javascript
const Search = require("./search");
const search = new Search();

// LISTENER 1: When search starts
search.on("SEARCH_STARTED", (term) => {
  console.log("Search started for term :", term);
});

// LISTENER 2: When there's an error
search.on("SEARCH_ERROR", (result) => {
  console.log(`Error in search for term "${result.term}"`, result.message);
});

// LISTENER 3: When search succeeds
search.on("SEARCH_SUCCESS", (result) => {
  console.log(`Search Completed for term "${result.term}"`, result.count);
});

// DO THE SEARCHES!
search.searchCount("error"); // Will fail on purpose
search.searchCount(); // Will fail (no search term)
search.searchCount("test"); // Will succeed
```

**What does `.on()` mean?**

- `.on("EVENT_NAME", callback)` means: "When EVENT_NAME happens, run this function"
- It's like setting an alarm: "When it's 7 AM, wake me up!"

---

## The Flow - Step by Step

Let's trace what happens when you run `search.searchCount("test")`:

1. **Check input**

   - "test" is not undefined → OK!

2. **Broadcast START**

   - Emits `SEARCH_STARTED` with "test"
   - Console prints: `"Search started for term : test"`

3. **Ask the API**

   - Calls `API.countMatches("test")`
   - Waits 100ms...
   - Gets random number (let's say 42)

4. **Broadcast SUCCESS**
   - Emits `SEARCH_SUCCESS` with `{count: 42, term: "test"}`
   - Console prints: `"Search Completed for term "test" 42"`

---

## Key JavaScript Concepts

### 1. **Promises**

Promises handle asynchronous operations (things that take time).

```javascript
// Creating a promise
new Promise((resolve, reject) => {
  // Do something that takes time
  if (success) {
    resolve(result); // Success!
  } else {
    reject(error); // Failure!
  }
});

// Using a promise
somePromise
  .then((result) => {
    /* handle success */
  })
  .catch((error) => {
    /* handle error */
  });
```

### 2. **EventEmitter**

Allows objects to send and receive messages (events).

```javascript
// Create an emitter
class MyClass extends EventEmitter {}
const obj = new MyClass();

// Listen for events
obj.on("MY_EVENT", (data) => {
  console.log("Event received!", data);
});

// Send events
obj.emit("MY_EVENT", "Hello!");
// Prints: "Event received! Hello!"
```

### 3. **Classes**

Templates for creating objects.

```javascript
class Dog {
  bark() {
    console.log("Woof!");
  }
}

const myDog = new Dog();
myDog.bark(); // "Woof!"
```

### 4. **require/module.exports**

How JavaScript files share code.

```javascript
// In helper.js
module.exports = function sayHi() {
  console.log("Hi!");
};

// In main.js
const sayHi = require("./helper");
sayHi(); // "Hi!"
```

---

## What Happens When You Run It?

```bash
npm start
```

**Output:**

```
Search started for term : error
Search started for term : undefined
Search started for term : test
Error in search for term "undefined" INVALID_TERM
Error in search for term "error" CONNECTION_ERROR
Search Completed for term "test" 67
```

**Why this order?**

1. All three searches start immediately (non-blocking)
2. The undefined one fails instantly (no API call)
3. The other two wait for the API (100ms)
4. They finish in the order they complete

---

## Real-World Analogy

Imagine a restaurant:

- **search.js** = The waiter taking orders
- **mock-api.js** = The kitchen making food
- **index.js** = Customers listening for their order number
- **Events** = The announcement system ("Order #42 is ready!")

When you order:

1. Waiter announces: "Order received!" (SEARCH_STARTED)
2. Kitchen cooks (Promise waiting)
3. Either:
   - "Order #42 ready!" (SEARCH_SUCCESS)
   - "Sorry, we're out of that!" (SEARCH_ERROR)

---

## Summary

This code demonstrates:

- **Asynchronous programming** (Promises)
- **Event-driven architecture** (EventEmitter)
- **Object-oriented programming** (Classes)
- **Modular design** (separate files for different jobs)

It's a great example of how real applications handle searches, API calls, and events!
