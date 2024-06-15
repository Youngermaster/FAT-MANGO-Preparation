output = 0
# ! First Case
n = 5
t = 40
p = [10, 20, 200]
np = [100, 300]

# * Uncomment the following cases to test the code
# # ! Second Case
# n = 1
# t = 1
# p = []
# np = [64]

# # ! Third Case
# n = 1
# t = 113
# p = [355]
# np = []

store = 0


while len(p) > 0 or len(np) > 0:
  if len(p) == 0 or len(np) == 0:
    for i in p:
      store += i
    for i in np:
      store += i
    output = store / t
    break

  # Priority download
  dp = (t * 0.75) / len(p)
  # Non-priority download
  ndp = (t * 0.25) / len(np)

  print(dp, ndp)
  print("Priority queue: ", p)
  print("Non-priority queue: ", np)
  for i in range(len(p)):
    p[i] -= dp
    if p[i] <= 0:
      store += dp
      p.pop(i)
      break
  for i in range(len(np)):
    np[i] -= ndp
    if np[i] <= 0:
      store += ndp
      np.pop(i)
      break
  

print(output)


