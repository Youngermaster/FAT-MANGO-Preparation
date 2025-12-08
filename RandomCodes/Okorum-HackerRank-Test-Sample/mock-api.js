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

module.exports.countMatches = countMatches;
