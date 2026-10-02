# Teach-back prompts — lecture 01 (Uninformed Search)

One prompt per approved core keyword. For each, (a) explain the term in your own words,
without quoting the slides, and (b) explain how it relates to at least one other core
keyword from this lecture. Write your answers somewhere else; no answers are given here.

## 1. Search Problem

(a) In your own words, what makes something a "search problem" in this lecture's sense?
Name the pieces you have to supply before any algorithm can run, and say why the task
environment restrictions (fully observable, deterministic, static, discrete) are stated
up front rather than as an afterthought.

(b) Relate it to **State Space Graph**: what exactly does the formulation give you that
makes the graph drawable, and which piece of the formulation becomes which part of the
graph?

## 2. State Space Graph

(a) In your own words, what is a state space graph, and what do its vertices, edges, and
edge weights stand for?

(b) Relate it to **Search Tree**: the lecture introduces the graph and then immediately
says we rarely build it. Explain what the tree gives you that the graph does not, and
what you give up in exchange.

## 3. Search Tree

(a) In your own words, what is a search tree, and why does the lecture stress that
unexplored nodes are not in memory?

(b) Relate it to **Node Expansion** or to **Frontier**: describe how the tree grows over
time, and say which part of it is "finished" and which part is still live.

## 4. Frontier

(a) In your own words, what is the frontier, and what job does it do that the tree itself
does not do?

(b) Relate it to **Depth-First Search**, **Breadth-First Search**, or **Uniform-Cost
Search**: pick one and explain how its choice of frontier ordering produces its
particular guarantees. Try to state the general claim — that the frontier ordering is the
only thing that changes between the algorithms — and then defend it with your example.

## 5. Node Expansion

(a) In your own words, what happens when a node is expanded? List what gets created and
what gets stored, and explain why a node needs a parent pointer at all.

(b) Relate it to **Frontier**: describe the pop-expand-insert loop, and say why the goal
test is applied before expansion rather than after. What would break if a state could be
inserted without ever being checked against what has already been reached?

## 6. Depth-First Search

(a) In your own words, how does DFS decide what to look at next, and what does its
behavior look like when it fails to find a goal down a branch?

(b) Relate it to **Breadth-First Search**: state both of their space complexities and
explain, in terms of what each keeps in the frontier, why one is linear and the other is
exponential. Then say why neither is optimal in general.

## 7. Breadth-First Search

(a) In your own words, how does BFS decide what to look at next, and in what precise
sense is it "optimal"? Be careful to state the condition the optimality depends on.

(b) Relate it to **Uniform-Cost Search**: describe a search problem where BFS returns a
solution that UCS would not, and explain which property of the cost function makes the
two algorithms agree or disagree.

## 8. Uniform-Cost Search

(a) In your own words, what does UCS order the frontier by, and why does that ordering
mean that the first goal popped is reached by the cheapest path?

(b) Relate it to **Node Expansion** or **Frontier**: explain the two situations in which
a node gets added to the frontier, and why the second one (a cheaper path to a state
already reached) is needed for UCS but never arises as an issue for BFS run on uniform
costs.
