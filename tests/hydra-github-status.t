use strict;
use warnings;
use Test::More;
use HTTP::Response;
use JSON::MaybeXS;
use Hydra::Plugin::GithubStatus;

# Exercise the real notifier module with two independent evaluations and a
# captured HTTP transport. A dependent failure must never inherit another
# build's repository or commit; a cached notification must bind its new eval.
{
    package Rows;
    sub new { my ($class, @rows) = @_; bless { rows => \@rows }, $class }
    sub next { shift @{$_[0]->{rows}} }
    package Evaluation;
    sub new { my ($class, $id, $repo, $sha) = @_; bless { id => $id, flake => "github:PseudoDesign/$repo/$sha?narHash=sha256-test" }, $class }
    sub id { $_[0]->{id} }
    sub flake { $_[0]->{flake} }
    package Jobset;
    sub new { my ($class, $project) = @_; bless { project => $project, name => "main" }, $class }
    sub get_column { $_[0]->{$_[1]} }
    package Build;
    sub new { my ($class, %args) = @_; bless \%args, $class }
    sub jobset { Jobset->new($_[0]->{project}) }
    sub get_column { $_[0]->{$_[1]} }
    sub id { $_[0]->{id} }
    sub finished { $_[0]->{finished} }
    sub buildstatus { $_[0]->{status} }
    sub jobsetevals { Rows->new(@{$_[0]->{evals}}) }
}

my @requests;
my $code = 201;
{
    no warnings 'redefine';
    *LWP::UserAgent::request = sub {
        my ($self, $request) = @_;
        push @requests, $request;
        my $response = HTTP::Response->new($code);
        $response->header('X-RateLimit-Limit' => 5000);
        $response->header('X-RateLimit-Remaining' => 4999);
        $response->header('X-RateLimit-Reset' => time() + 3600);
        $response->content('sensitive response must not be logged');
        return $response;
    };
}

my $plugin = Hydra::Plugin::GithubStatus->new(config => {
    base_uri => 'https://hydra.example.test',
    githubstatus => {
        jobs => 'kaiba-(infra|provisioning):main:.*',
        authorization => 'Bearer test_only_token',
        inputs => 'src', excludeBuildFromContext => 1, useShortContext => 1,
    },
});
my $old = Evaluation->new(1, 'kaiba-infra', 'a' x 40);
my $dependent_eval = Evaluation->new(2, 'kaiba-provisioning', 'b' x 40);
my $fresh = Evaluation->new(3, 'kaiba-infra', 'c' x 40);
my $build = Build->new(id => 10, project => 'kaiba-infra', job => 'aarch64-linux.selector',
    finished => 1, status => 1, evals => [$old, $fresh]);
my $dependent = Build->new(id => 20, project => 'kaiba-provisioning', job => 'aarch64-linux.copied-storage-vm',
    finished => 1, status => 2, evals => [$dependent_eval]);
$plugin->buildFinished($build, [$dependent]);
is(scalar @requests, 3, 'reports both source revisions and the dependent revision');
like('' . $requests[-1]->uri, qr{/kaiba-provisioning/statuses/b{40}$}, 'dependent status uses its own evaluation');
is(decode_json($requests[-1]->content)->{state}, 'failure', 'dependent failure is visible');

@requests = ();
$build->{status} = 0;
$plugin->cachedBuildFinished($fresh, $build);
is(scalar @requests, 1, 'cached event only reports the corresponding new evaluation');
like('' . $requests[0]->uri, qr{/kaiba-infra/statuses/c{40}$}, 'cached success uses the new commit');
is(decode_json($requests[0]->content)->{state}, 'success', 'cached success is reported');
unlike(decode_json($requests[0]->content)->{context}, qr/:10$/, 'context does not include a changing build ID');

@requests = ();
$build->{finished} = 0;
$plugin->buildQueued($build);
is(decode_json($requests[0]->content)->{state}, 'pending', 'queued build is pending');

$code = 503;
eval { $plugin->buildStarted($build) };
like($@, qr/GitHub status request failed: HTTP 503/, 'HTTP failure throws for Hydra durable retries');
unlike($@, qr/sensitive response/, 'HTTP failure does not echo response bodies');
done_testing();
