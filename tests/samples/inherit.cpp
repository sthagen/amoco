#include <stdio.h>
#include <iostream>

using std::cout;
using std::endl;

class ClassA
{
	private:
		int v1;

	public:
		virtual int sum(int x, int y){
			return x+y;
		}

		virtual void vf1(){
			cout << "A->vf1" << endl;
		}
};

class ClassB
{
	public:
		virtual void vf2() {
			cout << "B->vf2" << endl;
		}
};

class ClassC: public ClassA, public ClassB
{
	private:
		int v1;
		int v2;

	public:
		ClassC() {
			v1 = 1;
			v2 = 2;
		}
		virtual void vf3() {
			cout << "C->vf3" << endl;
		}
		virtual void vf2(){
			cout << "C->vf2" << endl;
		}
};

int main(int argc, char ** argv, char **envp) {

	ClassB *b = new ClassB();
    b->vf2();
	ClassC *c = new ClassC();
	c->vf1();
	c->vf2();
	c->vf3();
	delete(c);
}
